import json
import os
from collections import defaultdict

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use('Agg')


def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def count_attributes(data, attribute):
    count = defaultdict(lambda: {'M': 0, 'F': 0, 'positive': 0, 'negative': 0})
    total_count = {'M': 0, 'F': 0}

    for song in data:
        gender = song['biogender']
        if gender not in ['M', 'F']:
            continue
        if attribute == 'themes':
            for item in song[attribute]:
                count[item][gender] += 1
                count[item]['positive'] += song['positive']
                count[item]['negative'] += song['negative']
        else:
            count[song[attribute]][gender] += 1
        total_count[gender] += 1

    return count, total_count


def count_combined_sentiments(data):
    count = defaultdict(lambda: {'M': 0, 'F': 0})
    total_count = {'M': 0, 'F': 0}

    for song in data:
        gender = song['biogender']
        if gender not in ['M', 'F']:
            continue
        count['positive'][gender] += song['positive']
        count['negative'][gender] += song['negative']
        total_count[gender] += song['positive'] + song['negative']

    # Round to 1 decimal place for positive and negative sentiments
    for sentiment in ['positive', 'negative']:
        for gender in ['M', 'F']:
            count[sentiment][gender] = round(count[sentiment][gender], 1)

    return count, total_count


def calculate_percentages(count, total_count):
    percentage = {}
    for item, counts in count.items():
        percentage[item] = {
            'M': round((counts['M'] / total_count['M']) * 100, 1) if total_count['M'] > 0 else 0,
            'F': round((counts['F'] / total_count['F']) * 100, 1) if total_count['F'] > 0 else 0
            }
    return percentage


def generate_table(count, percentage, columns, include_sentiments=False):
    table_data = []
    for item, counts in count.items():
        row = [item, counts['M'], f"{percentage[item]['M']:.1f}", counts['F'], f"{percentage[item]['F']:.1f}"]
        if include_sentiments:
            row.extend([round(counts['positive'], 1), round(counts['negative'], 1)])
        table_data.append(row)
    return pd.DataFrame(table_data, columns=columns)


def get_distinct_colors(n):
    colors = []
    golden_ratio_conjugate = 0.618033988749895
    hue = 0
    for i in range(n):
        hue += golden_ratio_conjugate
        hue %= 1
        rgb = mcolors.hsv_to_rgb([hue, 0.9, 0.9])  # Higher saturation and value for more vibrant colors
        colors.append(mcolors.rgb2hex(rgb))
    return colors

def autopct_generator(limit):
    def inner_autopct(pct):
        return ('%.1f%%' % pct) if pct > limit else ''
    return inner_autopct

def generate_pie_charts(count, title, filename):
    os.makedirs('plots', exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))

    labels = list(count.keys())
    sizes_m = [count[item]['M'] for item in labels]
    sizes_f = [count[item]['F'] for item in labels]
    colors = get_distinct_colors(len(labels))

    # Create a color map for consistent coloring using truncated labels
    color_map = {label: colors[i % len(colors)] for i, label in enumerate(labels)}

    # Filter out zero values
    filtered_labels_m = [label for label, size in zip(labels, sizes_m) if size > 0]
    filtered_sizes_m = [size for size in sizes_m if size > 0]
    filtered_labels_f = [label for label, size in zip(labels, sizes_f) if size > 0]
    filtered_sizes_f = [size for size in sizes_f if size > 0]

    filtered_colors_m = [color_map[label] for label in filtered_labels_m]
    filtered_colors_f = [color_map[label] for label in filtered_labels_f]

    ax1.pie(
        filtered_sizes_m,
        startangle=140,
        labeldistance=1.1,
        textprops={'fontsize': 8},
        colors=filtered_colors_m,
        autopct=autopct_generator(1),
        pctdistance=1.2  # Position the percentage labels outside the pie
    )
    ax1.set_title(f'{title} - Male')

    ax2.pie(
        filtered_sizes_f,
        startangle=140,
        labeldistance=1.1,
        textprops={'fontsize': 8},
        colors=filtered_colors_f,
        autopct=autopct_generator(1),
        pctdistance=1.2  # Position the percentage labels outside the pie
    )
    ax2.set_title(f'{title} - Female')

    # Add legend
    legend_labels = [f'{label}' for label in labels]
    fig.legend(legend_labels, loc='lower center', ncol=5)
    plt.subplots_adjust(bottom=0.25)
    plt.savefig(f'plots/{filename}.png')
    plt.close()


def save_table_as_image(df, filename):
    fig, ax = plt.subplots(figsize=(10, 6))  # Adjust the size as needed
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
    plt.savefig(f'plots/{filename}.png', bbox_inches='tight')
    plt.close()


def save_table_as_csv(df, filename):
    df.to_csv(f'plots/{filename}.csv', index=False)


def main():
    data = load_data('sanremo.json')

    # Themes
    themes_count, total_themes_count = count_attributes(data, 'themes')
    themes_percentage = calculate_percentages(themes_count, total_themes_count)
    themes_df = generate_table(
        themes_count,
        themes_percentage,
        ['Theme', 'Count M', 'Percentage M', 'Count F', 'Percentage F', 'Positive Sentiment', 'Negative Sentiment'],
        include_sentiments=True
        )
    save_table_as_image(themes_df, 'theme_table')
    save_table_as_csv(themes_df, 'theme_table')
    generate_pie_charts(themes_count, 'Theme Distribution', 'theme_pies')

    # Genres
    genre_count, total_genre_count = count_attributes(data, 'genre')
    genre_percentage = calculate_percentages(genre_count, total_genre_count)
    genre_df = generate_table(
        genre_count, genre_percentage, ['Genre', 'Count M', 'Percentage M', 'Count F', 'Percentage F']
        )
    save_table_as_image(genre_df, 'genre_table')
    save_table_as_csv(genre_df, 'genre_table')
    generate_pie_charts(genre_count, 'Genre Distribution', 'genre_pies')

    # Combined Sentiments
    sentiment_count, total_sentiment_count = count_combined_sentiments(data)
    sentiment_percentage = calculate_percentages(sentiment_count, total_sentiment_count)
    sentiment_df = generate_table(
        sentiment_count, sentiment_percentage, ['Sentiment', 'Count M', 'Percentage M', 'Count F', 'Percentage F']
        )
    save_table_as_image(sentiment_df, 'sentiment_table')
    save_table_as_csv(sentiment_df, 'sentiment_table')
    generate_pie_charts(sentiment_count, 'Sentiment Distribution', 'sentiment_pies')


if __name__ == "__main__":
    main()
