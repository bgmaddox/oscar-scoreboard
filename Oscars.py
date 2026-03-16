import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
import os
import re
import pytz
from datetime import datetime
from streamlit_extras.let_it_rain import rain
import streamlit_extras
from streamlit_autorefresh import st_autorefresh
import requests
from io import StringIO

# --- 1. Page Config ---
st.set_page_config(
    page_title="Oscar Scoreboard",
    page_icon="🌟",
    layout="wide",
)



# --- 2. Constants & Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTER_DIR = os.path.join(BASE_DIR, "OscarPosters")
PLACEHOLDER_IMG = os.path.join(POSTER_DIR, "Placeholder.png")

SCORES_MAP = {
    "Best Director (15 pts)":15, "Best Lead Actor (15 pts)":15, "Best Lead Actress (15 pts)":15,
    "Best Supporting Actress (15 pts)":15, "Best Supporting Actor (15 pts)":15,
    "Best Adapted Screenplay (15 pts)":15, "Best Original Screenplay (15 pts)":15,
    "Best Cinematography (10 pts)":10, "Best Animated Feature Film (10 pts)":10,
    "Best Original Song (10 pts)":10, "Best Original Score (10 pts)":10,
    "Best International Feature Film (10 pts)":10, "Best Animated Short Film (5 pts)":5,
    "Best Documentary Feature (5 pts)":5, "Best Documentary Short Subject (5 pts)":5,
    "Best Film Editing (5 pts)":5, "Best Makeup and Hairstyling (5 pts)":5,
    "Best Production Design (5 pts)":5, "Best Visual Effects (5 pts)":5,
    "Best Live Action Short Film (5 pts)":5, "Best Costume Design (5 pts)":5,
    "Best Sound (5 pts)":5, "Which film will win the most Oscars? (10 pts)":10,
    "Best Casting (10 pts)":10,
    "Best Picture (20 pts)":20
}

# --- 3. Optimized Data Loading ---
Winner_SHEET_URL = "https://docs.google.com/spreadsheets/d/1ivt0monzA-ymjJcCEPKyLbc8_9vvLSDhCDsocg6YW8E/export?format=csv"

# Cache the picks FOREVER (since they don't change tonight)
@st.cache_data
def load_static_data():
    
    try:
        # Option 1: Try to get data from the web using 'requests' (More )
        response = requests.get(Winner_SHEET_URL)
        response.raise_for_status() # Check if the download actually worked
        
        # Convert the text string into a format pandas can read
        data = StringIO(response.text)
        df = pd.read_csv(data)
        df = df.drop(['Timestamp','Venmo Username (so I can pay you if you win)'], axis = 1)
        
        # Clean up data
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        
        return df

    except Exception as e:
        # Option 2: If the internet fails, silently fall back to the local CSV
        print(f"⚠️ Network error: {e}")
        print("⚠️ Switching to local backup file.")
        
        pool_path = os.path.join(BASE_DIR, "Oscar Pool 2026 Responses.csv")
        df = pd.read_csv(pool_path)
        df = df.drop(['Timestamp','Venmo Username (so I can pay you if you win)'], axis = 1)
        # Clean whitespace once
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        return df

# Cache the winners for 30 SECONDS (checks for updates frequently)
LIVE_SHEET_URL = "https://docs.google.com/spreadsheets/d/18a5kfac7R7kkV3yk4Kk0Ff3zk2sqrL1nuHKfYza4-CA/export?format=csv"

#https://docs.google.com/spreadsheets/d/18a5kfac7R7kkV3yk4Kk0Ff3zk2sqrL1nuHKfYza4-CA/edit?usp=sharing

@st.cache_data(ttl=60)
def load_live_data():
    try:
        # Option 1: Try to get data from the web using 'requests' (More )
        response = requests.get(LIVE_SHEET_URL)
        response.raise_for_status() # Check if the download actually worked
        
        # Convert the text string into a format pandas can read
        data = StringIO(response.text)
        winners = pd.read_csv(data)
        
        # Clean up data
        winners = winners.map(lambda x: x.strip() if isinstance(x, str) else x)
        winners['Points'] = winners['Category'].map(get_points_from_category)
        # --- THE GHOST KILLER ---
        # Forces the app to ignore the Tiebreaker row or any extra notes in your Google Sheet
        winners = winners[winners['Category'].isin(SCORES_MAP.keys())]
        
        return winners

    except Exception as e:
        # Option 2: If the internet fails, silently fall back to the local CSV
        print(f"⚠️ Network error: {e}")
        print("⚠️ Switching to local backup file.")
        
        backup_path = os.path.join(BASE_DIR, "2026 Oscar Winners.csv")
        winners = pd.read_csv(backup_path)
        winners = winners.map(lambda x: x.strip() if isinstance(x, str) else x)
        winners['Points'] = winners['Category'].map(get_points_from_category)
        # --- THE GHOST KILLER ---
        # Forces the app to ignore the Tiebreaker row or any extra notes in your Google Sheet
        winners = winners[winners['Category'].isin(SCORES_MAP.keys())]
        return winners
    

def get_points_from_category(category_name):
    match = re.search(r"\((\d+)", str(category_name))
    return int(match.group(1)) if match else 10

# --- 4. CSS Injection ---
custom_css = """
<style>
    table { font-family: 'Courier New', monospace !important; font-size: 18px !important; }
    thead th { font-size: 20px !important; font-weight: bold; color: #FF4B4B; }
    td { height: 50px !important; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 5. Helper Functions ---

def get_poster_path(movie_name):
    if not movie_name or pd.isna(movie_name):
        return None
    clean_name = str(movie_name).strip()
    for ext in [".jpg", ".jpeg", ".png"]:
        path = os.path.join(POSTER_DIR, clean_name + ext)
        if os.path.exists(path):
            return path
    return None

def render_category_card(row, df_picks):
    category = row['Category']
    winner = row['Winner Movie']
    
    with st.container(border=True):
        st.subheader(category)
        inner_col1, inner_col2 = st.columns([1, 1.5]) 
        
        with inner_col1:
            image_path = get_poster_path(winner)
            if image_path:
                st.image(image_path, caption=winner, width=150)
            elif winner and pd.notna(winner):
                st.warning(f"No poster: {winner}")
            else:
                if os.path.exists(PLACEHOLDER_IMG):
                    st.image(PLACEHOLDER_IMG, caption="To be announced", width=150)
                else:
                    st.info("Pending...")

        with inner_col2:
            try:
                chart_data = df_picks[[category, 'Username']].copy()
                chart_data.columns = ['Nominee', 'Username']
                chart_data['Count'] = 1

                fig = px.bar(
                    chart_data, x='Count', y='Nominee', color='Username',
                    text='Username', orientation='h', title=None,
                    color_discrete_sequence=px.colors.qualitative.Antique
                )

                # --- NEW SIMPLIFIED TROPHY LOGIC ---
                if winner and pd.notna(winner) and str(winner).strip() != "":
                    # Create a list of winning movies (handles 1 winner or comma-separated ties)
                    winning_movies = [w.strip().lower() for w in str(winner).split(',')]
                    
                    # Loop through all nominees and drop a trophy on any that match
                    for nominee in chart_data['Nominee'].unique():
                        if str(nominee).strip().lower() in winning_movies:
                            fig.add_annotation(
                                x=0,                     
                                y=nominee,               
                                text="🍿",
                                showarrow=False,
                                xanchor="left",          
                                xshift=10,               
                                font=dict(size=30) 
                            )

                fig.update_layout(
                    height=250, margin=dict(l=0, r=0, t=0, b=0),
                    xaxis_title=None, yaxis_title=None,
                    yaxis={'categoryorder':'total ascending','tickfont':dict(size=15)},
                    showlegend=False, coloraxis_showscale=False,
                    uniformtext_minsize=12, uniformtext_mode='hide',
                    barcornerradius=13
                )
                fig.update_traces(textposition='inside', insidetextanchor='middle',
                                  hovertemplate='%{text}<extra></extra>')

                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{category}")

            except KeyError:
                st.error(f"Data error: Could not find column '{category}'")

def calculate_scoreboard(df_picks, df_winners):
    scoreboard = df_picks.copy()
    
    # --- 1. Standard Score Calculation ---
    if 'Username' in scoreboard.columns:
        scoreboard['Contestant'] = scoreboard['Username']

    actual_winners_dict = df_winners.set_index('Category')['Winner'].to_dict()
    
    # This matches the exact string you provided
    tiebreak_col = "TIEBREAK (Closest): The film with the most wins will have how many Oscars?"
    
    # If the user prompt didn't have the question mark, use this version:
    # tiebreak_col = "TIEBREAK (Closest): The film with the most wins will have how many Oscars"
    # Ensure this matches your CSV header EXACTLY.
    
    valid_cols = []
    for category in df_picks.columns:
        # We process standard categories normally
        if category in actual_winners_dict and category in SCORES_MAP and category != tiebreak_col:
            valid_cols.append(category)
            correct_answer = actual_winners_dict[category]
            points = SCORES_MAP[category]
            
            # Robust comparison
            # --- TIE FIX: Support comma-separated winners ---
            # Split the correct answer(s) into a list of cleaned strings
            valid_answers = [ans.strip().lower() for ans in str(correct_answer).split(',')]
            
            # Check if the user's pick is inside that list of valid answers
            user_picks_clean = df_picks[category].astype(str).str.strip().str.lower()
            is_correct = user_picks_clean.isin(valid_answers)
            
            scoreboard[category] = is_correct.astype(int) * points
        elif category not in ["Username", "Contestant", tiebreak_col]: 
            scoreboard[category] = 0

    # Sum totals (excluding the tiebreak column itself for now)
    numeric_cols = [c for c in valid_cols if c in scoreboard.columns]
    scoreboard['Total Score'] = scoreboard[numeric_cols].sum(axis=1)
    
    # --- 2. Tiebreak Logic ---
    # Retrieve the actual tiebreak answer (if it exists)
    actual_tiebreak_val = actual_winners_dict.get(tiebreak_col)
    
    # Create a temporary column for sorting
    # Default to a high number (Infinity) so people aren't ranked if no answer exists yet
    scoreboard['Tiebreak Diff'] = float('inf') 

    # Only run logic if the Tiebreak Answer has been entered in the Winners CSV
    if pd.notna(actual_tiebreak_val) and str(actual_tiebreak_val).strip() != "":
        try:
            # Convert actual answer to a number (e.g., "7")
            target = float(str(actual_tiebreak_val).strip())
            
            # Calculate absolute difference for EVERYONE (in case of ties for 2nd/3rd place too)
            # We coerce errors='coerce' to turn text into NaN, then fill with infinity
            user_guesses = pd.to_numeric(scoreboard[tiebreak_col], errors='coerce').fillna(float('inf'))
            scoreboard['Tiebreak Diff'] = abs(user_guesses - target)
            
        except ValueError:
            pass # If data is messy, we skip tiebreak sorting

    # --- 3. Final Sorting & Ranking ---
    # Sort primarily by Total Score (Descending), Secondarily by Tiebreak Diff (Ascending/Lower is better)
    scoreboard = scoreboard.sort_values(
        by=['Total Score', 'Tiebreak Diff'], 
        ascending=[False, True]
    )
    
    # Create Rank: Method='min' means if 2 people are tied perfectly (same score + same diff), they share the rank
    scoreboard['Rank'] = scoreboard[['Total Score', 'Tiebreak Diff']].apply(tuple, axis=1).rank(method='min', ascending=False).astype(int)
    
    return scoreboard

    
    

def style_row_by_groups(row):
    COLOR_PALETTE = ["#ffadad", "#ffd6a5", "#fdffb6", "#caffbf", "#9bf6ff", "#a0c4ff", "#bdb2ff", "#ffc6ff"]
    unique_values = row.unique()
    value_to_color = {val: COLOR_PALETTE[i % len(COLOR_PALETTE)] for i, val in enumerate(unique_values)}
    return [f'background-color: {value_to_color.get(val, "")}; color: black' for val in row]

def get_biggest_sniper(df_picks, df_winners):
    """
    Finds the correct pick that was chosen by the FEWEST number of people.
    Returns: (Category, Winner, List of Snipers, Count)
    """
    best_snipe_count = float('inf')
    best_snipe_info = None

    # Convert winners to dict for fast lookup
    winners_dict = df_winners.set_index('Category')['Winner'].to_dict()

    for category, winner in winners_dict.items():
        if pd.notna(winner) and winner != "":
            # Get everyone's picks for this category
            all_picks = df_picks[category].astype(str).str.strip().str.lower()
            winner_clean = str(winner).strip().lower()
            
            # Find who picked it
            correct_pickers = df_picks[all_picks == winner_clean]['Username'].tolist()
            count = len(correct_pickers)
            
            # We look for the lowest count that is greater than 0
            if 0 < count < best_snipe_count:
                best_snipe_count = count
                best_snipe_info = (category, winner, correct_pickers)
            # Tie-breaker: If counts are equal, maybe prioritize higher point categories? 
            # (Skipping for simplicity)

    return best_snipe_info

# --- 6. Main App Execution ---

# Load Data Separately
df = load_static_data() # Loads once
Winners = load_live_data() # Loads every 30s
Scoreboard = calculate_scoreboard(df, Winners)

# 2. CHECK FOR NEW WINNERS (The Trophy Rain)
if 'awards_count' not in st.session_state:
    st.session_state['awards_count'] = 0

current_awards_count = Winners['Winner'].notna().sum()

if current_awards_count > st.session_state['awards_count']:
    # THIS IS THE NEW PART
    rain(
        emoji="🏆",
        font_size=54,
        falling_speed=7,
        animation_length=1, # Rains for 1 second
    )
    st.toast("🚨 NEW WINNER ANNOUNCED!", icon="🏆", duration='long')
    
    # Update state
    st.session_state['awards_count'] = current_awards_count

# 3. CALCULATE SCOREBOARD
Scoreboard = calculate_scoreboard(df, Winners)

Scoreboard_Lite = Scoreboard[['Contestant', 'Total Score', 'Rank']]

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Scoreboard", "Live Winners", "Picks", "Head-to-Head", "Path to Victory", "Rooting Guide", "Pool Stats & Trivia"])

# --- TAB 1: SCOREBOARD ---
with tab1:
    header_img = os.path.join(BASE_DIR, "Oscar Pool.png") 
    if os.path.exists(header_img):
        st.image(header_img)

    # --- START OF NEW BADGE LOGIC ---
    # 1. Find the last 3 categories that have a winner announced
    awarded_cats = Winners[Winners['Winner'].notna() & (Winners['Winner'] != "")]
    recent_cats = awarded_cats.tail(3)['Category'].tolist()

    def get_streak_icon(row):
        # If fewer than 3 awards have been given, no badges yet
        if len(recent_cats) < 3:
            return ""
        
        # Check if the user earned points (> 0) in these recent categories
        # We access the row's data for these specific column names
        correct_count = 0
        for cat in recent_cats:
            if row[cat] > 0: 
                correct_count += 1
        
        if correct_count == 3: return "🔥" # Got all 3 right
        if correct_count == 0: return "❄️" # Got all 3 wrong
        return "" # Normal

    # 2. Apply the badge to a new 'Status' column
    Scoreboard['Status'] = Scoreboard.apply(get_streak_icon, axis=1)
    # --------------------------------

    CurrentWinner = Scoreboard.set_index('Contestant')['Total Score'].idxmax()

    cols = st.columns([1,.8,1])

    with cols[0].container(border=True):
        st.markdown("### Scoreboard")
        
        # 3. Update the display to include the Status column (Rank, Status, Contestant, Total Score)
        Scoreboard_Lite = Scoreboard[['Rank', 'Status', 'Contestant', 'Total Score']]
        st.table(Scoreboard_Lite.set_index("Rank"), border='horizontal')

    with cols[1].container(border=False):
        is_awarded = Winners['Winner'].notna() & (Winners['Winner'] != "")
        points_awarded = Winners.loc[is_awarded, 'Points'].sum()
        points_left = Winners.loc[~is_awarded, 'Points'].sum()

        st.metric('Current Winner', value=CurrentWinner)
        st.divider()
        st.metric('Points Awarded', value=int(points_awarded))
        st.divider()
        st.metric('Points Left', value=int(points_left))
        
        st.divider()
        snipe_info = get_biggest_sniper(df, Winners)
        if snipe_info:
            category, movie, snipers = snipe_info
            # Join names with commas if multiple people sniped it
            sniper_names = ", ".join(snipers)
            
            st.info(f"🎯 **The Sniper Award**: Only {len(snipers)} person(s) correctly picked **'{movie}'** for *{category}*!")
            st.write(f"👏 Applause for: **{sniper_names}**")
        st.divider()
        # Get current time in EST (or your local time)
        tz = pytz.timezone('US/Eastern')
        current_time = datetime.now(tz).strftime("%I:%M %p")
            
        st.write(f"🔄 Last Updated: **{current_time}**")

        # --- AUTO-REFRESH TOGGLE ---
        # Default is True (On)
        # If a user is annoyed by the reloading, they can uncheck this box.
        enable_autorefresh = st.checkbox("Live Auto-Refresh On/Off (60s)", value=False)
        
        if enable_autorefresh:
            # This will trigger a rerun every 60 seconds
            st_autorefresh(interval=60000, limit=None, key="oscar_auto_refresher")
        
        
            
        if st.button("Force Refresh Data"):
                st.cache_data.clear()
                st.rerun()

    with cols[2].container(border=True):
        st.markdown("### Leading Movies")
        if not Winners['Winner Movie'].dropna().empty:
             OscarCount = Winners[Winners['Winner Movie'] != ""].groupby('Winner Movie')['Points'].count().sort_values(ascending=False)
             if not OscarCount.empty:
                 OscarLeader = OscarCount.idxmax()
                 OscarLeaders = OscarCount.head().reset_index()
             else:
                 OscarLeader = None
                 OscarLeaders = pd.DataFrame(columns=['Winner Movie','Points'])
        else:
            OscarLeader = None
            OscarLeaders = pd.DataFrame(columns=['Winner Movie','Points'])

        cent_co = st.columns([1, 2, 1])[1]
        with cent_co:
            if OscarLeader:
                poster = get_poster_path(OscarLeader)
                if poster:
                    st.image(poster, caption=f"Leader: {OscarLeader}", width=250)
                else:
                    st.warning(f"No poster: {OscarLeader}")
            else:
                if os.path.exists(PLACEHOLDER_IMG):
                    st.image(PLACEHOLDER_IMG, caption="Waiting...", width=200)

        if not OscarLeaders.empty:
            st.table(OscarLeaders.set_index("Winner Movie"), border='horizontal')

    chart_cols = [c for c in Scoreboard.columns if c in SCORES_MAP]
    figScoreBar = px.bar(Scoreboard, y="Contestant", x=chart_cols, orientation='h', template='plotly_dark',
                         color_discrete_sequence=px.colors.qualitative.Antique)

    figScoreBar.update_layout(
        legend=dict(orientation="h", yanchor="top", y=-.25, xanchor="right", x=1),
        showlegend=False, height=700, yaxis={'categoryorder':'total ascending', 'title' : "", 'tickfont':dict(size = 18)},
        barcornerradius = 13, xaxis = dict(title = "", tickfont = dict(size = 20)),
        
    )
    figScoreBar.update_traces(
        textposition='inside', insidetextanchor='middle',
        hovertemplate='<b>%{data.name}</b><br>Points: %{x}<br>Contestant: %{y}<extra></extra>'
    )

    
    # Calculate progress
    total_cats = len(SCORES_MAP)
    awarded_cats = Winners['Winner'].notna().sum()
    pct_complete = awarded_cats / total_cats
    
    st.write(f"**Ceremony Progress:** {awarded_cats}/{total_cats} Categories")
    st.progress(pct_complete)
    
    
    st.divider()


    # --- RACE CHART LOGIC ---
    st.markdown("### The Race So Far")

    # 1. Filter to only awarded categories
    awarded_cats = Winners[Winners['Winner'].notna() & (Winners['Winner'] != "")].copy()

    if not awarded_cats.empty:
        # 2. Sort by the new 'Order' column
        # We convert to numeric first to ensure '10' comes after '2'
        if 'Order' in awarded_cats.columns:
            awarded_cats['Order'] = pd.to_numeric(awarded_cats['Order'], errors='coerce')
            awarded_cats = awarded_cats.sort_values('Order')
        
        # 3. Build the cumulative history
        history_data = []
        
        # Initialize scores at 0
        current_tallies = {user: 0 for user in Scoreboard['Contestant']}
        
        # Add a "Start" point (Time 0) so lines start at 0
        for user in current_tallies:
            history_data.append({
                "Category Label": "Start", 
                "User": user, 
                "Score": 0
            })

        # Track the exact order of labels for the X-axis
        x_axis_order = ["Start"]

        # Loop through categories in the correct 'Order'
        for idx, row in awarded_cats.iterrows():
            cat = row['Category']
            winner = row['Winner']
            points = row['Points']
            
            # Clean the Name: "Best Picture (20 pts)" -> "Best Picture"
            clean_cat = cat.split('(')[0].strip()
            x_axis_order.append(clean_cat)
            
            # Update scores for this category
            for user in current_tallies:
                # Look up the user's pick
                # (We use the main 'df' to find the pick)
                user_pick = df.loc[df['Username'] == user, cat].values[0]
                
                if str(user_pick).strip().lower() == str(winner).strip().lower():
                    current_tallies[user] += points
            
            # Record the new scores
            for user, score in current_tallies.items():
                history_data.append({
                    "Category Label": clean_cat, 
                    "User": user, 
                    "Score": score
                })
        
        # 4. Plot
        race_df = pd.DataFrame(history_data)
        
        fig_race = px.line(
            race_df, 
            x="Category Label", 
            y="Score", 
            color="User", 
            markers=True,
            title="",
            color_discrete_sequence=px.colors.qualitative.Antique,
            line_shape='spline'
        )
        
        fig_race.update_traces(hovertemplate='%{y} pts')

        # 5. Lock the X-Axis Order and Format
        fig_race.update_layout(
            xaxis=dict(
                title=None,
                type='category',
                # This is crucial: Force the axis to follow our chronological list
                categoryorder='array',
                categoryarray=x_axis_order,
                # Angle the text so long names don't overlap
                tickangle=-65,
                tickfont = dict(size = 17) 
            ),
            yaxis_title="Total Score",
            hovermode="x unified",
            height=800, # Made slightly taller to accommodate angled labels
            legend=dict(orientation="h", y=1.2),
        )
        
        st.plotly_chart(fig_race, use_container_width=True)
    else:
        st.info("Waiting for the first award to be announced to generate the Race Chart...")


    st.plotly_chart(figScoreBar, use_container_width=True)


# --- TAB 2: LIVE WINNERS ---
with tab2:
    st.header("🏆 98th Academy Award Winners")
    for i in range(0, len(Winners), 2):
        cols = st.columns(2)
        with cols[0]:
            render_category_card(Winners.iloc[i], df)
        if i + 1 < len(Winners):
            with cols[1]:
                render_category_card(Winners.iloc[i+1], df)

# --- TAB 3: EVERYONE'S PICKS ---
with tab3:
    # Create a dropdown for unannounced categories
    st.markdown("### Unannounced Breakdown")
    unannounced_cats = [c for c in SCORES_MAP.keys() 
                        if c not in Winners['Category'].values 
                        or pd.isna(Winners.set_index('Category').loc[c, 'Winner'])]

    if unannounced_cats:
        selected_battle = st.selectbox("See the split for unannounced categories:", unannounced_cats)
        
        # Count the picks
        counts = df[selected_battle].value_counts().reset_index()
        counts.columns = ['Nominee', 'Count']
        
        fig = px.pie(counts, values='Count', names='Nominee', title=f"Group Picks for {selected_battle}",
                    hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(legend=dict(
                                orientation="h",
                                yanchor="top",
                                x=.5,
                                y=-.2,
                                xanchor="center",
                                font=dict(
                                            # family="Courier",
                                            size=18,
                                            color="white"
                                        )
                                    ),
                                )
        fig.update_traces(textfont_size = 30)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("All categories announced!")
    PicksTurned = df.set_index('Username').T
    # --- PREVENT DUPLICATE NAME CRASH ---
    if PicksTurned.columns.duplicated().any():
        cols = pd.Series(PicksTurned.columns)
        PicksTurned.columns = cols + cols.groupby(cols).cumcount().astype(str).replace('0', '')
    # ------------------------------------
    styled_df = PicksTurned.style.apply(style_row_by_groups, axis=1).set_properties(
        **{'inline-size': '10px', 'overflow-wrap': 'break-word'}
    )
    st.divider()
    st.markdown("### 📊 Category Difficulty")

    difficulty_data = []
    # Only check awarded categories
    for idx, row in Winners.iterrows():
        winner = row['Winner']
        if pd.notna(winner) and winner != "":
            cat = row['Category']
            
            # Calculate how many people got it right
            # We compare the entire column of picks for this category against the winner
            correct_picks = df[cat].map(lambda x: str(x).strip().lower() == str(winner).strip().lower()).sum()
            percent_correct = (correct_picks / len(df)) * 100
            
            difficulty_data.append({"Category": cat, "Percent Correct": percent_correct})

    if difficulty_data:
        diff_df = pd.DataFrame(difficulty_data).sort_values("Percent Correct")
        
        # Color logic: Red = Hard, Green = Easy
        fig_diff = px.bar(diff_df, x="Percent Correct", y="Category", orientation='h',
                        text="Percent Correct",
                        color="Percent Correct",
                        color_continuous_scale="RdYlGn", # Red to Yellow to Green
                        range_color=[0, 100])
        
        fig_diff.update_layout(yaxis_title=None, xaxis_title="% of Pool Correct", height=400, coloraxis_showscale=False, 
                               xaxis = dict(tickfont = dict(size = 20))
                            , yaxis = dict(title = "", tickfont = dict(size = 15)))
        fig_diff.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
        st.plotly_chart(fig_diff, use_container_width=True)
    st.divider()  
    st.markdown("### Everyone's Picks")
    #st.dataframe(styled_df, height=1100, use_container_width=True)
    st.dataframe(PicksTurned, height=1100, use_container_width=True)

    

# --- TAB 4: HEAD TO HEAD ---
with tab4:
    st.header("⚔️ Head-to-Head Comparison")
    comp_df = df.set_index('Username')
    users = list(comp_df.index.unique())
    
    col1, col2 = st.columns(2)
    with col1:
        user1 = st.selectbox("Select First Person", users, index=0)
    with col2:
        default_index = 1 if len(users) > 1 else 0
        user2 = st.selectbox("Select Second Person", users, index=default_index)

    # --- NEW ERROR CHECK ---
    if user1 == user2:
        st.warning("⚠️ You are comparing the same person! Please select a different user.")
        st.stop() # This halts the script here so the table doesn't load below
    # -----------------------

    if user1 and user2:
        comparison_df = comp_df.loc[[user1, user2]].T
        matches = (comparison_df[user1] == comparison_df[user2]).sum()
        differences = len(comparison_df) - matches
        agreement_pct = (matches / len(comparison_df)) * 100

        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1: st.metric("Agreed Picks", matches)
        with m_col2: st.metric("Different Picks", differences, delta_color="inverse")
        with m_col3: st.metric("Agreement %", f"{agreement_pct:.1f}%")
        
        st.divider()

        show_diff_only = st.checkbox("Show only differences")
        if show_diff_only:
             comparison_df = comparison_df[comparison_df[user1] != comparison_df[user2]]

        def highlight_diff(row):
            val1, val2 = row[0], row[1]
            if pd.isna(val1) and pd.isna(val2): color = '#caffbf'
            elif val1 != val2: color = '#ffadad'
            else: color = '#caffbf'
            return [f'background-color: {color}; color: black'] * 2

        st.dataframe(comparison_df.style.apply(highlight_diff, axis=1), use_container_width=True, height=1000)

# --- TAB 5: PATH TO VICTORY ---
with tab5:
    st.header("🚀 Path to Victory Calculator")
    path_df_base = df.set_index('Username')
    users = list(path_df_base.index.unique())
    hero_user = st.selectbox("Who are you rooting for?", users, key = "rooting_select")
    
    if hero_user:
        current_leader_row = Scoreboard.iloc[0]
        leader_name = current_leader_row['Contestant']
        leader_score = current_leader_row['Total Score']
        
        if leader_name == hero_user:
            if len(Scoreboard) > 1:
                target_row = Scoreboard.iloc[1]
                target_name = target_row['Contestant']
                target_score = target_row['Total Score']
                is_winning = True
            else:
                st.success("You win!"); st.stop()
        else:
            target_name = leader_name
            target_score = leader_score
            is_winning = False
            
        hero_score = Scoreboard.loc[Scoreboard['Contestant'] == hero_user, 'Total Score'].values[0]
        gap = target_score - hero_score

        st.metric(f"Current Status vs {target_name}", f"{hero_score} pts", 
                  delta=f"{'-' if not is_winning else '+'}{abs(gap)} pts")

        if not is_winning:
            max_gain = 0
            path_data = []
            winners_dict = Winners.set_index('Category')['Winner'].to_dict()

            for category, points in SCORES_MAP.items():
                winner = winners_dict.get(category)
                is_decided = pd.notna(winner) and winner != ""
                
                if not is_decided:
                    if category in path_df_base.columns and hero_user in path_df_base.index:
                        my_pick = str(path_df_base.loc[hero_user, category]).strip()
                    else:
                        # Fallback if the category or user isn't in this dataframe
                        my_pick = "N/A"
                    if category in path_df_base.columns and target_name in path_df_base.index:
                        target_pick = str(path_df_base.loc[target_name, category]).strip()
                    else:
                        target_pick = "N/A"
                    
                    if my_pick != target_pick:
                        max_gain += points
                        path_data.append({
                            "Category": category,
                            "Points": points,
                            "Your Pick": my_pick,
                            "Leader's Pick": target_pick
                        })
            
            st.divider()
            if max_gain >= gap:
                st.success(f"POSSIBLE! You can gain up to {max_gain} points.")
                st.dataframe(pd.DataFrame(path_data), use_container_width=True)
            else:
                st.error(f"Mathematically Eliminated. Max possible gain: {max_gain}. Gap: {gap}.")
    with tab6:
            # --- ROOTING GUIDE LOGIC ---
        st.markdown("### 📣 Rooting Guide (Unannounced Categories)")

        # Filter for categories that do NOT have a winner yet
        unannounced = [c for c in SCORES_MAP.keys() if c not in Winners['Category'].values 
                    or pd.isna(Winners.set_index('Category').loc[c, 'Winner'])]

        if unannounced:
            # Let user pick the upcoming category from a dropdown
            target_cat = st.selectbox("What category is coming up next?", unannounced,
                                      key="unannounced_guide_select")
            
            # Create a nice dataframe of who picked what
            # 1. Get picks for this category
            picks = df[['Username', target_cat]].rename(columns={target_cat: 'Pick'})
            
            # 2. Group by the movie picked
            grouped = picks.groupby('Pick')['Username'].apply(list).reset_index()
            
            # 3. Add counts for sorting
            grouped['Count'] = grouped['Username'].apply(len)
            grouped = grouped.sort_values('Count', ascending=False)
            
            # 4. Display as a clean grid
            for index, row in grouped.iterrows():
                movie = row['Pick']
                people = row['Username']
                count = row['Count']
                
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        st.metric("Votes", count)
                    with c2:
                        st.subheader(movie)
                        st.write(", ".join(people))
        else:
            st.balloons()
            st.success("All categories have been announced! The pool is closed!")
    with tab7:
        st.markdown("## 🍿 Pool Stats & Trivia")

        col1, col2 = st.columns(2)
        
        FunDF = df.set_index("Username").iloc[:, -2:]
        # ==========================================
        # GRAPH 1: FAVORITE MOVIE (Donut Chart)
        # ==========================================
        # --- Ensure Username is a column, not just the index ---
        df_temp = FunDF.copy()
        if 'Username' not in df_temp.columns:
            df_temp = df_temp.reset_index()
            # If the index was unnamed, it might default to 'index', so we rename it
            if 'index' in df_temp.columns and 'Username' not in df_temp.columns:
                df_temp = df_temp.rename(columns={'index': 'Username'})
        
        # ==========================================
        # GRAPH 1: FAVORITE MOVIE (Donut Chart)
        # ==========================================
        with col1:
            st.markdown("#### The Group's Favorite Movie")
            
            # 1. Group by movie, count the votes, and join the usernames with a line break
            fav_agg = df_temp.groupby('Favorite Movie').agg(
                Votes=('Username', 'count'),
                Users=('Username', lambda x: '<br>'.join(x))
            ).reset_index()
            
            fig_fav = px.pie(
                fav_agg, 
                values='Votes', 
                names='Favorite Movie', 
                hole=0.4,
                custom_data=['Users'], # Sneak the text list into the plot data
                color_discrete_sequence=px.colors.qualitative.Antique
            )
            
            fig_fav.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                # Custom hover: Bold movie label, vote count, then the list of names
                hovertemplate="<b>%{label}</b><br>Votes: %{value}<br><br><b>Picked by:</b><br>%{customdata[0]}<extra></extra>"
            )
            
            fig_fav.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_fav, use_container_width=True)
        
        
        # ==========================================
        # GRAPH 2: MOST WATCHED MOVIES (Bar Chart)
        # ==========================================
        with col2:
            st.markdown("#### Most Watched Movies")
            
            # 1. Keep only Username and Movies Seen, drop empty rows
            seen_df = df_temp[['Username', 'Movies Seen']].dropna().copy()
            
            # 2. Split the comma string into lists
            seen_df['Movies Seen'] = seen_df['Movies Seen'].astype(str).str.split(',')
            
            # 3. Explode the lists so each movie gets its own row WITH the Username still attached
            seen_exploded = seen_df.explode('Movies Seen')
            seen_exploded['Movies Seen'] = seen_exploded['Movies Seen'].str.strip()
            
            # 4. Group by the movie, count them, and join the usernames
            seen_agg = seen_exploded.groupby('Movies Seen').agg(
                Watch_Count=('Username', 'count'),
                Users=('Username', lambda x: '<br>'.join(x))
            ).reset_index()
            
            # 5. Sort and take the Top 10
            seen_top10 = seen_agg.sort_values('Watch_Count', ascending=False).head(10)
            
            fig_seen = px.bar(
                seen_top10, 
                x='Watch_Count', 
                y='Movies Seen', 
                orientation='h',
                custom_data=['Users'], # Sneak the text list in
                color='Watch_Count',
                color_continuous_scale="Teal"
            )
            
            fig_seen.update_layout(
                yaxis={'categoryorder':'total ascending'},
                xaxis_title="Number of Contestants Who Saw It",
                yaxis_title=None,
                coloraxis_showscale=False,
                margin=dict(t=30, b=0, l=0, r=0)
            )
            
            # --- NEW: Force the X-axis to count by 1s ---
            fig_seen.update_xaxes(dtick=1) 
            
            fig_seen.update_traces(
                # Custom hover: Bold movie label, then just the list of people
                hovertemplate="<b>%{y}</b><br><br><b>Watched by:</b><br>%{customdata[0]}<extra></extra>"
            )
    
            st.plotly_chart(fig_seen, use_container_width=True)
