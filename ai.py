import json
import os

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


# Prepare the prompt for the OpenAI API
def prepare_prompt(song, themes):
    example_output = {
        "genre": "...",
        "themes": ["...", "...", "..."],
        "positive": 0.5,
        "negative": 0.5
    }
    prompt = (
        f"Classifica il seguente brano musicale:\n\n"
        f"Testo:\n{song['lyrics']}\n\n"
        f"Temi possibili:\n{', '.join(themes)}\n\n"
        f"Restituisci un JSON con il genere, un array dei temi principali (massimo 3), "
        f"e le percentuali di sentimenti positivi e negativi da 0 a 1.\n\n"
        f"Esempio di output:\n{json.dumps(example_output, ensure_ascii=False, indent=4)}"
    )
    return prompt

# Call the OpenAI API to classify the song
def classify_song(song, themes):
    api_key = os.getenv('OPENAI_API_KEY')
    client = OpenAI(api_key=api_key)
    prompt = prepare_prompt(song, themes)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content.strip())


# Update the songs with the information returned by the API
def update_songs(songs, themes):
    classifications = [classify_song(song, themes) for song in songs]
    for song, classification in zip(songs, classifications):
        song['genre'] = classification.get('genre', '')
        song['themes'] = classification.get('themes', [])
        song['positive'] = classification.get('positive', 0)
        song['negative'] = classification.get('negative', 0)
    return songs


# Save the updated songs to the file sanremo.json
def save_songs(songs, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(songs, file, ensure_ascii=False, indent=4)


def main():
    themes = ["Gioventù", "Crescita e Identità", "Amore e Relazioni", "Famiglia e Legami", "Solitudine e Isolamento",
              "Turbamenti Interiori e Salute Mentale", "Contesto Sociale e Culturale", "Memoria e Nostalgia",
              "Autonomia ed Empowerment"]

    print("Loading songs from 'sanremo.json'...")
    songs = load_songs('sanremo.json')
    print(f"Loaded {len(songs)} songs.")

    print("Updating songs...")
    updated_songs = update_songs(songs, themes)
    print("Songs updated.")

    print("Saving updated songs to 'sanremo.json'...")
    save_songs(updated_songs, 'sanremo.json')
    print("Songs saved successfully.")

if __name__ == "__main__":
    main()
