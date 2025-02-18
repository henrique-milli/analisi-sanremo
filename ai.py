import json
import os
import sys

from openai import OpenAI


# avoid using python-dotenv
def load_dotenv(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Load environment variables from the .env file
load_dotenv('.env')

# Load songs from the file sanremo.json
def load_songs(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


# Load themes from the file labels.json
def load_labels(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        labels = json.load(file)
        return labels['temi_principali'], labels['generi_musicali']


# Call the OpenAI API to extract themes from the songs via a two-step process.
def extract_labels(songs):
    # First call: get the detailed internal chain-of-thought
    chain_thought = extract_chain_of_thought(songs)
    # Second call: derive the JSON answer from the chain-of-thought output
    return infer_labels_from_cot(chain_thought)


def extract_chain_of_thought(songs):
    api_key = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)
    prompt = get_themes_cot_prompt(songs)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
        )
    return response.choices[0].message.content.strip()


def infer_labels_from_cot(chain_thought):
    api_key = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)
    prompt = get_themes_json_prompt(chain_thought)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
        )
    return json.loads(response.choices[0].message.content.strip())


def get_themes_cot_prompt(songs):
    prompt = (
        "Analizza in dettaglio i testi dei seguenti brani musicali per identificare i temi principali e il genere musicale. "
        "Per ciascun brano, esegui un ragionamento passo dopo passo, esaminando emozioni, immagini, narrazioni, "
        "correlazioni tra i testi e caratteristiche musicali. Non fornire il risultato finale, ma solo il tuo ragionamento completo.\n\n"
    )
    for song in songs:
        prompt += f"## Titolo: {song['song']}\n\n"
        prompt += f"Testo:\n{song['lyrics']}\n\n"
    prompt += "Fornisci il tuo ragionamento completo."
    return prompt


def get_themes_json_prompt(chain_thought):
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "temi_principali": {
                "type": "array",
                "items": {
                    "type": "string"
                    },
                "uniqueItems": True
                },
            "generi_musicali": {
                "type": "array",
                "items": {
                    "type": "string"
                    },
                "uniqueItems": True
                }
            },
        "required": ["temi_principali", "generi_musicali"]
        }

    prompt = (
        "Basandoti sul ragionamento seguente, estrai un JSON che rappresenta i temi principali e i generi musicali dei testi. "
        "Includi i temi principali e comuni senza duplicati, formattati come etichette di una o due parole. "
        "Includi anche i generi musicali rilevanti per ciascun testo.\n\n"
        f"{chain_thought}\n\n"
        f"Rispondi solamente con un JSON che rispetti il seguente schema:\n{schema}"
    )
    return prompt


# Save themes to the file labels.json
def save_labels(labels, file_path):
    with open(file_path, 'w+', encoding='utf-8') as file:
        json.dump(labels, file, ensure_ascii=False, indent=4)


# Get the prompt for song classification with internal chain-of-thought
def get_classification_prompt(song, themes, genres):
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "genre": {
                "type": "string"
                },
            "themes": {
                "type": "array",
                "items": {
                    "type": "string"
                    },
                "maxItems": 3
                },
            "positive": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
                },
            "negative": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
                }
            },
        "required": ["genre", "themes", "positive", "negative"]
        }
    prompt = (
        "Analizza il seguente brano musicale e classificalo in base ai seguenti criteri:\n"
        "1. Genere musicale: seleziona uno tra i generi possibili elencati.\n"
        "2. Temi principali: seleziona al massimo 3 tra i temi possibili elencati.\n"
        "3. Sentimenti: indica le percentuali (da 0 a 1) di sentimenti positivi e negativi nel testo.\n\n"
        f"Testo del brano:\n{song['lyrics']}\n\n"
        f"Generi possibili: {', '.join(genres)}\n\n"
        f"Temi possibili: {', '.join(themes)}\n\n"
        "Rispondi solamente con un JSON che rispetti il seguente JSON schema:\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=4)}"
    )
    return prompt

# Call the OpenAI API to classify the song
def classify(song, themes, genres):
    api_key = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)
    prompt = get_classification_prompt(song, themes, genres)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content.strip())

# Update the songs with the information returned by the API
def update_songs(songs, themes, genres):
    classifications = [classify(song, themes, genres) for song in songs]
    for song, classification in zip(songs, classifications):
        song['genre'] = classification.get('genre', '')
        song['themes'] = classification.get('themes', [])
        song['positive'] = classification.get('positive', 0)
        song['negative'] = classification.get('negative', 0)
    return songs

# Save the updated songs to the file sanremo.json
def save_songs(songs, file_path):
    with open(file_path, 'w+', encoding='utf-8') as file:
        json.dump(songs, file, ensure_ascii=False, indent=4)

def main():
    update_labels = '--labels' in sys.argv

    print("Loading songs from 'sanremo.json'...")
    songs = load_songs('sanremo.json')
    print(f"Loaded {len(songs)} songs.")

    if update_labels:
        print("Extracting labels from songs...")
        labels = extract_labels(songs)
        themes = labels['temi_principali']
        genres = labels['generi_musicali']
        print("Labels extracted.")

        print("Saving labels to 'labels.json'...")
        save_labels(labels, 'labels.json')
        print("Themes saved successfully.")
    else:
        print("Loading labels from 'labels.json'...")
        themes, genres = load_labels('labels.json')
        print(f"Loaded {len(themes)} themes and {len(genres)} genres.")

    print("Updating songs...")
    updated_songs = update_songs(songs, themes, genres)
    print("Songs updated.")

    print("Saving updated songs to 'sanremo.json'...")
    save_songs(updated_songs, 'sanremo.json')
    print("Songs saved successfully.")

if __name__ == "__main__":
    main()
