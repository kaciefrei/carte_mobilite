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
def process_csv(file):
    try:
        # Essayer de charger le CSV avec une détection automatique du séparateur
        df = pd.read_csv(file, sep=None, engine='python')
        df["Ville"] = df["Ville"].str.strip()

        # Comptage des occurrences par ville
        df_count = df["Ville"].value_counts().reset_index()
        df_count.columns = ["Ville", "Occurrences"]

        # Ajout des coordonnées géographiques
        df_count[["Latitude", "Longitude"]] = df_count["Ville"].apply(lambda x: pd.Series(get_lat_lon(x)))

        return df_count

    except pd.errors.ParserError:
        st.error("Erreur lors du traitement du fichier CSV. Veuillez vérifier son format.")
        return None

# 2. Nettoyage et agrégation des données
def clean_data(df):
    df["Ville"] = df["Ville"].str.strip().str.lower()
    df_grouped = df.groupby("Ville", as_index=False).agg({
        "Occurrences": "sum",
        "Latitude": "first",
        "Longitude": "first"
    })
    df_grouped["Ville"] = df_grouped["Ville"].str.title()
    return df_grouped

# 3. Création de la carte interactive
def create_map(df, circle_size, circle_color, region_width, region_color):
    # Charger les contours des régions françaises
    gdf = gpd.read_file("https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/regions.geojson")
    bourgogne_fc = gdf[gdf["nom"] == "Bourgogne-Franche-Comté"]

    # Création de la carte
    m = folium.Map(location=[47, 5], zoom_start=8)

    # Ajout des contours de la région avec une largeur et une couleur ajustable
    folium.GeoJson(
        bourgogne_fc.to_json(),
        name="Bourgogne-Franche-Comté",
        style_function=lambda x: {"color": region_color, "weight": region_width, "fillOpacity": 0}
    ).add_to(m)

    # Ajout des villes avec leur occurrence et des cercles ajustables
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

    # Sauvegarde de la carte dans un fichier HTML
    map_html = "carte_bfc_nombre_mobilite_24_25.html"
    m.save(map_html)
    return map_html

# Streamlit interface
st.title("Analyse de Mobilité BFC 🌍")

# Upload CSV
uploaded_file = st.file_uploader("Choisis un fichier CSV", type="csv")

# Paramètres interactifs
circle_size = st.slider("Taille des cercles (valeur par défaut : 0.4)", min_value=0.1, max_value=1.0, value=0.4, step=0.1)
circle_color = st.color_picker("Choisir la couleur des cercles", "#0000FF")
region_width = st.slider("Largeur de la ligne délimitant la région (valeur par défaut : 3)", min_value=1, max_value=10, value=3)
region_color = st.color_picker("Choisir la couleur de la délimitation de la région", "#FF0000")

# Bouton pour lancer l'analyse
if uploaded_file is not None:
    
    start_analysis = st.button("Créer la carte")

    if start_analysis:
        with st.spinner('Chargement et traitement du fichier...'):
            # Étape 1 : Traitement du CSV
            df_count = process_csv(uploaded_file)
            
            if df_count is not None:
                # Étape 2 : Nettoyage et agrégation
                df_grouped = clean_data(df_count)

                # Étape 3 : Création de la carte avec les paramètres choisis
                with st.spinner('Création de la carte...'):
                    map_html = create_map(df_grouped, circle_size, circle_color, region_width, region_color)
                
                st.markdown("Carte générée, clique pour la télécharger :")
                
                # Afficher un lien pour télécharger la carte
                with open(map_html, "r") as f:
                    st.download_button(
                        label="Télécharger la carte",
                        data=f,
                        file_name=map_html,
                        mime="text/html"
                    )
