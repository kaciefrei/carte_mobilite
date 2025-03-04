import pandas as pd
import geopandas as gpd
import folium
import streamlit as st
from opencage.geocoder import OpenCageGeocode
from io import StringIO

# Clé API pour OpenCage Geocoder
API_KEY = "132d20febbef4dada95928d714005a02"
geocoder = OpenCageGeocode(API_KEY)

# Fonction pour obtenir la latitude et la longitude d'une ville
def get_lat_lon(ville):
    result = geocoder.geocode(ville + ", Bourgogne Franche Comté, France")
    if result:
        return result[0]['geometry']['lat'], result[0]['geometry']['lng']
    return None, None

# 1. Chargement et traitement du fichier de mobilité
def process_csv_bfc(file):
    try:
        df = pd.read_csv(file, sep=None, engine='python')
        df["Ville"] = df["Ville"].str.strip()
        df_count = df["Ville"].value_counts().reset_index()
        df_count.columns = ["Ville", "Occurrences"]
        df_count[["Latitude", "Longitude"]] = df_count["Ville"].apply(lambda x: pd.Series(get_lat_lon(x)))
        return df_count
    except pd.errors.ParserError:
        st.error("Erreur lors du traitement du fichier CSV. Veuillez vérifier son format.")
        return None

# 2. Nettoyage et agrégation des données
def clean_data_bfc(df):
    df["Ville"] = df["Ville"].str.strip().str.lower()
    df_grouped = df.groupby("Ville", as_index=False).agg({
        "Occurrences": "sum",
        "Latitude": "first",
        "Longitude": "first"
    })
    df_grouped["Ville"] = df_grouped["Ville"].str.title()
    return df_grouped

# 3. Création de la carte interactive BFC
def create_map_bfc(df, circle_size, circle_color, region_width, region_color):
    gdf = gpd.read_file("https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions.geojson")
    bourgogne_fc = gdf[gdf["nom"] == "Bourgogne-Franche-Comté"]
    m = folium.Map(location=[47, 5], zoom_start=8)
    folium.GeoJson(bourgogne_fc.to_json(), style_function=lambda x: {"color": region_color, "weight": region_width, "fillOpacity": 0}).add_to(m)
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=row['Occurrences'] * circle_size,
            popup=f"{row['Ville']} ({row['Occurrences']})",
            color=circle_color,
            fill=True,
            fill_color=circle_color,
            fill_opacity=0.6,
        ).add_to(m)
    map_html = "carte_bfc_nombre_mobilite_24_25.html"
    m.save(map_html)
    return map_html

# Fonction pour obtenir la latitude et la longitude d'une ville
def get_lat_lon_europe(ville, destination):
    location = f"{ville}, {destination}"
    result = geocoder.geocode(location)
    if result:
        return result[0]['geometry']['lat'], result[0]['geometry']['lng']
    return None, None

# Traitement du fichier de mobilité Europe
def process_csv_europe(file):
    try:
        df = pd.read_csv(file, sep=None, engine='python')
        if df.columns.duplicated().any():
            df = df.loc[:, ~df.columns.duplicated(keep="last")]
        if "Ville.1" not in df.columns:
            st.error("Erreur : La colonne 'Ville.1' est introuvable dans le fichier CSV.")
            return None
        df_count = df.groupby(["Destination", "Ville.1"]).size().reset_index(name="Occurrences")
        df_count[["Latitude", "Longitude"]] = df_count.apply(lambda row: pd.Series(get_lat_lon_europe(row['Ville.1'], row['Destination'])), axis=1)
        missing_locations = df_count[df_count["Latitude"].isna()]
        df_count = df_count.dropna(subset=["Latitude", "Longitude"])
        if not missing_locations.empty:
            st.warning("Les villes suivantes n'ont pas pu être géolocalisées :\n" + ", ".join(missing_locations["Ville.1"].unique()))
        return df_count
    except pd.errors.ParserError:
        st.error("Erreur lors du traitement du fichier CSV. Veuillez vérifier son format.")
        return None

# Création de la carte interactive Europe
def create_map_europe(df, circle_size, circle_color):
    m = folium.Map(location=[50, 10], zoom_start=4)
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=row['Occurrences'] * circle_size,
            popup=f"{row['Destination']} - {row['Ville.1']} ({row['Occurrences']})",
            color=circle_color,
            fill=True,
            fill_color=circle_color,
            fill_opacity=0.6,
        ).add_to(m)
    map_html = "carte_europe_destinations.html"
    m.save(map_html)
    return map_html

# Configuration de la page Streamlit
st.set_page_config(page_title="Carte de Mobilité et Destinations 🌍", page_icon="🌍")

# Ajout d'une description dynamique sous le titre
st.markdown('<div class="description">Sélectionne une option pour explorer les données de mobilité et de destinations.</div>', unsafe_allow_html=True)

# Affichage des gros boutons animés pour choisir entre les cartes
option = st.radio(
    "Choisir l'option",
    ["Carte de Mobilité BFC 🌍", "Carte des Destinations en Europe 🌍"],
    key="toggle",
    index=0,
    horizontal=True,
    help="Sélectionne l'option pour afficher la carte correspondante",
    label_visibility="collapsed"
)

# Affichage en fonction de l'option choisie
if option == "Carte de Mobilité BFC 🌍":
    st.title("Analyse de Mobilité BFC 🌍")
    uploaded_file = st.file_uploader("Choisir un fichier CSV", type="csv")
    circle_size = st.slider("Taille des cercles", min_value=0.1, max_value=1.0, value=0.4, step=0.1)
    circle_color = st.color_picker("Couleur des cercles", "#f7ce3c")
    region_width = st.slider("Largeur de la ligne délimitant la région", min_value=1, max_value=10, value=3)
    region_color = st.color_picker("Couleur de la délimitation", "#250671")

    if uploaded_file is not None:
        start_analysis = st.button("Créer la carte")
        if start_analysis:
            with st.spinner('Chargement et traitement du fichier...'):
                df_count = process_csv_bfc(uploaded_file)
                if df_count is not None:
                    df_grouped = clean_data_bfc(df_count)
                    with st.spinner('Création de la carte...'):
                        map_html = create_map_bfc(df_grouped, circle_size, circle_color, region_width, region_color)
                    st.markdown("Carte générée, clique pour la télécharger :")
                    with open(map_html, "r") as f:
                        st.download_button(label="Télécharger la carte", data=f, file_name=map_html, mime="text/html")

elif option == "Carte des Destinations en Europe 🌍":
    st.title("Carte des Destinations en Europe 🌍")
    uploaded_file = st.file_uploader("Choisir un fichier CSV", type="csv")
    circle_size = st.slider("Taille des cercles", min_value=0.1, max_value=1.0, value=0.4, step=0.1)
    circle_color = st.color_picker("Couleur des cercles", "#f7ce3c")

    if uploaded_file is not None:
        start_analysis = st.button("Créer la carte")
        if start_analysis:
            with st.spinner('Traitement du fichier...'):
                df_count = process_csv_europe(uploaded_file)
                if df_count is not None:
                    with st.spinner('Création de la carte...'):
                        map_html = create_map_europe(df_count, circle_size, circle_color)
                    st.markdown("Carte générée, clique pour la télécharger :")
                    with open(map_html, "r") as f:
                        st.download_button(label="Télécharger la carte", data=f, file_name=map_html, mime="text/html")
