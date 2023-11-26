import string
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from wordcloud import WordCloud, STOPWORDS
import warnings

warnings.filterwarnings("ignore")


def worldcloud_generator(sentences, background_color="black", max_words=200):
    """
    Parameters
    -----------
        sentences: a Pandas Series containg text.

    Returns
    -----------
        Wordcloud
    """

    # 1. cleaning data
    # 1.1 Apply lowercase
    sentences = sentences.str.lower()
    # print(sentences)
    # 1.2 Remove punctuation
    sentences = sentences.apply(
        lambda x: x.translate(str.maketrans("", "", string.punctuation))
    )

    # 2. Tokenizing
    # 2.1 Load stopwords
    stopwords = set(STOPWORDS)
    # 2.2 join all words
    txt = " ".join(sentences)
    # 2.3 Tokenizing
    tokens = word_tokenize(txt)
    # 2.4 Removing stopwords
    text_clean = [word for word in tokens if word not in stopwords]

    # 3. Generating the Word Cloud
    # 3.1 Generate the text
    text = " ".join(text_clean)
    # 3.2 Create a WordCloud object
    wordcloud = WordCloud(
        background_color=background_color,
        max_words=max_words,
        width=700,
        height=500,
        max_font_size=100,
        collocations=False,
    )
    # 4. Generate the word cloud
    wordcloud.generate(text)

    return wordcloud


def wordcloud_params(wc):
    """
    Get parameters of each word in the wordcloud (positions, size, color...).

    Parameters
    -----------
        wc: the Wordcloud.

    Returns
    -----------
        position_x_list: List of x positions
        position_y_list: List of y positions
        freq_list: Frequency of each common word in the wordcloud
        size_list: Size of each word (proportional to its frequency)
        color_list: Color of the word
        word_list: Most common words.

    References
    -----------
         https://github.com/PrashantSaikia/Wordcloud-in-Plotly
    """

    word_list = []
    freq_list = []
    fontsize_list = []
    position_list = []
    orientation_list = []
    color_list = []

    for (word, freq), fontsize, position, orientation, color in wc.layout_:
        word_list.append(word)
        freq_list.append(freq)
        fontsize_list.append(fontsize)
        position_list.append(position)
        orientation_list.append(orientation)
        color_list.append(color)

    # Get x and y positions
    position_x_list = []
    position_y_list = []
    for i in position_list:
        position_x_list.append(i[0])
        position_y_list.append(i[1])

    # Get the relative occurence frequencies --> word size
    size_list = []
    for i in freq_list:
        size_list.append(i * 100)

    # Return wordcloud parametres (positions, frequencies, colors...)
    return position_x_list, position_y_list, freq_list, size_list, color_list, word_list
