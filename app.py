# Part 1: Initialization & User Auth
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import re
from database import init_db, delete_station_entry
from database import save_station_entry
import ast
init_db()
import sqlite3
import matplotlib.pyplot as plt
from plotly.io import to_image
from PIL import Image



# ----------------- USER DATABASE ------------------
from database import register_user, authenticate_user, get_all_users, get_user_section, save_station_entry, load_station_data

# ----------------- SESSION FLAGS ------------------
for key in ["logged_in", "current_user", "active_page", "register_mode", "reset_mode", "analysis_unlocked", "logentry_unlocked"]:
    if key not in st.session_state:
        st.session_state[key] = None if key == "current_user" else False

# ----------------- REGISTRATION FORM ------------------
def registration_form():
    st.header("📝 Register New User")

    section_type = st.radio("Select Access Type", ["Log Entry", "Analysis Report (PIN Required)", "Both (PIN Required)"])

    selected_section = {
        "Log Entry": "log entry",
        "Analysis Report (PIN Required)": "analysis report",
        "Both (PIN Required)": "both"
    }[section_type]

    if selected_section in ["analysis report", "both"]:
        pin = st.text_input("🔐 Enter Admin PIN to Register", type="password")
        if pin != "1234":
            st.warning("🔐 Valid Admin PIN required to register this user.")
            return

    new_username = st.text_input("New Username")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Create User"):
        if new_password != confirm_password:
            st.error("❌ Passwords do not match.")
        else:
            register_user(
                new_username,
                new_password,
                selected_section,
                st.session_state.current_user or "unknown"
            )
            st.success(f"✅ User '{new_username}' created with '{selected_section}' access.")
            st.session_state.register_mode = False

# ----------------- RESET PASSWORD FORM ------------------
def reset_password_form():
    st.header("🔁 Reset Password")
    username = st.text_input("🔑 Username to Reset")
    new_pass = st.text_input("🔐 New Password", type="password")
    confirm = st.text_input("🔐 Confirm New Password", type="password")

    if st.button("Update Password"):
        if new_pass != confirm:
            st.error("❌ Passwords do not match.")
        else:
            register_user(username, new_pass, get_user_section(username), "updated")
            st.success(f"✅ Password reset for user '{username}'.")
            st.session_state.reset_mode = False

# ----------------- DOWNLOAD REGISTERED USERS ------------------
def download_user_list():
    st.subheader("📋 Registered Users List")

    df = get_all_users()
    st.dataframe(df)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, "registered_users.csv", "text/csv")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Registered Users Report", ln=True, align="C")
    for _, row in df.iterrows():
        pdf.cell(200, 10, txt=f"{row['Username']} | {row['Access']} | {row['Registered By']} | {row['Registered At']}", ln=True)

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    st.download_button("⬇️ Download PDF", pdf_output, "registered_users.pdf", "application/pdf")

# ----------------- LOGIN FLOW ------------------
if not st.session_state.logged_in:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = authenticate_user(username, password)
        if user:
            allowed_section = user[2]
            st.session_state.logged_in = True
            st.session_state.current_user = username
            st.session_state.analysis_unlocked = allowed_section in ["analysis report", "both"]
            st.session_state.logentry_unlocked = allowed_section in ["log entry", "both"]

            if allowed_section == "log entry":
                st.session_state.active_page = "log entry"
            elif allowed_section == "analysis report":
                st.session_state.active_page = "analysis report"
            elif allowed_section == "both":
                st.session_state.active_page = "log entry"

            st.success(f"✅ Login successful. Access granted: {allowed_section}")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Register"):
            st.session_state.register_mode = True
    with col2:
        if st.button("🔁 Reset Password"):
            st.session_state.reset_mode = True

    if st.session_state.register_mode:
        registration_form()
    elif st.session_state.reset_mode:
        reset_password_form()

    st.stop()

# ----------------- SIDEBAR INFO ------------------
st.sidebar.success(f"👤 Logged in as: {st.session_state.current_user}")

if st.session_state.current_user:
    section = get_user_section(st.session_state.current_user)
    st.sidebar.info(f"📄 Section Access: {section}")

    if section == "log entry":
        if st.session_state.active_page != "log entry":
            st.session_state.active_page = "log entry"
        st.sidebar.markdown("📝 Log Entry Access Only")

    elif section == "analysis report":
        if st.session_state.active_page != "analysis report":
            st.session_state.active_page = "analysis report"
        st.sidebar.markdown("📊 Analysis Report Access Only")

    elif section == "both":
        st.sidebar.markdown("🔀 Access to Log Entry and Analysis Report")
        st.sidebar.markdown(f"📄 Currently Viewing: **{st.session_state.active_page.title()}**")
        if st.sidebar.button("🔁 Switch Page"):
            st.session_state.active_page = (
                "analysis report" if st.session_state.active_page == "log entry" else "log entry"
            )

    if st.session_state.current_user == "admin":
        if st.sidebar.button("📋 View Users"):
            st.session_state.active_page = "admin_user_list"

if st.sidebar.button("🔓 Logout"):
    for key in [
        "logged_in", "active_page", "current_user",
        "analysis_unlocked", "logentry_unlocked",
        "register_mode", "reset_mode"
    ]:
        st.session_state[key] = False if key == "logged_in" else None
    st.rerun()


valid_zones = ["WZ", "EZ", "SZ", "NZ", "CZ", "SWZ", "NWZ", "SR", "TSPS", "Plant"]

zone_sps_map = {
    "WZ": ["Ranip", "Chenpur", "Motera", "Keshavnagar", "Sharda", "Paldi Shantivan"],
    "EZ": ["Rakhiyal", "Viratnagar", "Ambikanagar", "Rabari Vasahat", "Arbuda Nagar"],
    "SZ": ["Maninagar", "Vatva Nigam", "Isanpur-2"],
    "NZ": ["Naroda Gayatri", "Ambawadi"],
    "CZ": ["Shahibag", "Dariyapur", "Mirzapur"],
    "SWZ": ["Juhapura", "Vejalpur"],
    "NWZ": ["Ghuma", "Vasantnagar Gota"],
    "SR": ["W-5"],
    "TSPS": [
        "Jamalpur", "106 MLD", "NSP", "Danilimda", "Ambedkar", "180 MLD Pirana",
        "Pirana terminal", "Saijpur 7", "Maleksaban 30", "Kotarpur 60", "100 MLD Vinzol",
        "102 MLD Vinzol", "Lambha 17.50MLD", "SRFDCL E3", "Dafnala 25", "SRFDCL V.Baraj",
        "Vasna Auda 126 mld", "285 MLD Vasna", "Vasna 76 mld", "Jalvihar 60"
    ],
    "Plant": [
        "Old Pirana-106 MLD", "Old Pirana- 60 MLD", "New Pirana-180 MLD", "New Pirana-155 MLD",
        "Saijpur-7 MLD", "Maleksaban-30 MLD", "Kotarpur-60 MLD", "Vinzol-100 MLD",
        "Vinzol-70 MLD", "Vinzol-35 MLD", "Lambha-5 MLD", "Shankarbhuvan-25 MLD",
        "Dafnala-25 MLD", "Vasna-35 MLD", "Vasna-126 MLD", "Vasna-240 MLD",
        "Vasna-48 MLD", "Jalvihar-60 MLD"
    ]
}

# log entry page
if st.session_state.get("show_success"):
    st.success("✅ Entry saved successfully!")
    st.session_state["show_success"] = False

if st.session_state.active_page == "log entry":
    if not st.session_state.logentry_unlocked:
        st.error("🚫 You are not authorized to access the 'Log Entry' section.")
        st.stop()

    if "unlocked_entries" not in st.session_state:
        st.session_state["unlocked_entries"] = set()

    st.title("📝 Log Entry Page")

    if "selected_zone" not in st.session_state:
        st.session_state.selected_zone = valid_zones[0]

    selected_zone = st.selectbox("Zone", valid_zones, index=valid_zones.index(st.session_state.selected_zone))
    st.session_state.selected_zone = selected_zone
    sps_options = zone_sps_map.get(selected_zone, [])

    entry_date = date.today()
    entry_date_str = entry_date.strftime('%Y-%m-%d')

    submitted = False

    with st.form("log_entry_form"):
        col1, col2 = st.columns(2)
        entry_date = col1.date_input("Date", value=date.today())
        sps_name = col2.selectbox("SPS Name", sps_options)

        entry_date_str = entry_date.strftime('%Y-%m-%d')
        sps_name_normalized = sps_name.strip().lower()
        entry_key = f"{entry_date_str}_{sps_name_normalized}"

        col3, col4, col5, col6 = st.columns(4)
        total_pumps = col3.number_input("Total Pumps", min_value=0, step=1)
        working_pumps = col4.number_input("Working Pumps", min_value=0, step=1)
        standby_pumps = col5.number_input("Standby Pumps", min_value=0, step=1)
        standby_um = col6.number_input("Standby U/M", min_value=0, step=1)
        remarks = st.text_area("Remarks")

        if selected_zone == "Plant":
            col8, col9 = st.columns(2)
            income_mld = col8.number_input("Income MLD", min_value=0.0)
            supply_mld = col9.number_input("Supply MLD", min_value=0.0)
            pumping_mld = 0.0
        else:
            pumping_mld = st.number_input("Pumping MLD", min_value=0.0)
            income_mld = 0.0
            supply_mld = 0.0

        submitted = st.form_submit_button("📄 Submit Entry")

    if submitted:
        df_logs = load_station_data()
        df_logs["entry_date"] = pd.to_datetime(df_logs["entry_date"], errors='coerce').dt.strftime('%Y-%m-%d')
        df_logs["sps_name"] = df_logs["sps_name"].astype(str).str.strip().str.lower()

        match = df_logs[
            (df_logs["entry_date"] == entry_date_str) &
            (df_logs["sps_name"] == sps_name_normalized)
        ]

        if not match.empty and entry_key not in st.session_state.get("unlocked_entries", set()):
            st.session_state.pending_unlock = entry_key
            st.session_state.show_refresh = True
            st.warning("🔒 Entry already exists. Please delete or change SPS/date.")

            if st.button("🔄 Refresh", key="refresh_existing"):
                st.session_state.show_refresh = False
                st.session_state.pending_unlock = None
                st.rerun()

            st.stop()

        save_station_entry(
            entry_date_str, selected_zone.lower(), st.session_state.current_user, sps_name,
            total_pumps, working_pumps, standby_pumps, standby_um,
            remarks, pumping_mld, income_mld, supply_mld
        )
        st.session_state["show_success"] = True
        st.session_state["unlocked_entries"].discard(entry_key)
        st.rerun()

    if st.session_state.get("pending_unlock"):
        st.warning("🔒 This entry is locked. Please delete old entry or change SPS/date.")
        if st.button("🔄 Refresh to Delete or Change SPS/date", key="refresh_locked"):
            st.session_state.pending_unlock = None
            st.session_state.show_refresh = False
            st.rerun()

    st.subheader("📄 Recent Entries")
    selected_filter_date = st.date_input("🗓️ Filter by Date", date.today())
    df_user_logs = load_station_data()
    df_user_logs["entry_date"] = pd.to_datetime(df_user_logs["entry_date"], errors='coerce').dt.date

    selected_zone_norm = selected_zone.strip().lower()
    df_user_logs["zone"] = df_user_logs["zone"].astype(str).str.strip().str.lower()
    df_user_logs["sps_name"] = df_user_logs["sps_name"].astype(str).str.strip().str.lower()

    # Corrected filter for today
    filtered_logs = df_user_logs[
        (df_user_logs["zone"] == selected_zone_norm) &
        (df_user_logs["entry_date"] == selected_filter_date)
        ]

    if not filtered_logs.empty:
        df_recent_display = filtered_logs.copy()
        df_recent_display.reset_index(drop=True, inplace=True)
        df_recent_display.index += 1
        df_recent_display["Delete"] = df_recent_display.apply(
            lambda row: f"🗑️ Delete - {row['sps_name']} ({row['entry_date']})", axis=1)
        st.dataframe(df_recent_display.drop(columns=["Delete"]))

        for idx, row in filtered_logs.iterrows():
            if st.button(f"🗑️ Delete Entry - {row['sps_name']} ({row['entry_date']})", key=f"del_btn_{idx}"):
                delete_station_entry(
                    row['entry_date'].strftime("%Y-%m-%d"),
                    row['sps_name']
                )
                st.success("✅ Entry deleted.")
                st.rerun()
    else:
        st.info("ℹ️ No entries found for selected zone and date.")

    # Pending Entries fix (matches cleaned zone/SPS)
    today_logs = filtered_logs["sps_name"].tolist()
    sps_expected = [s.strip().lower() for s in zone_sps_map.get(selected_zone, [])]
    pending_today = [s for s in sps_expected if s not in today_logs]

    if pending_today:
        st.warning(f"🚧 Pending SPS entries for {selected_zone} on {selected_filter_date.strftime('%d-%m-%Y')}")
        df_pending = pd.DataFrame({"Pending SPS": pending_today})
        df_pending.reset_index(drop=True, inplace=True)
        df_pending.index += 1
        st.dataframe(df_pending)
    else:
        st.success("✅ All SPS entries completed for selected zone and date.")



####################################################################################################################################

# Always reload fresh station data when entering analysis report


if st.session_state.active_page == "analysis report":
    st.session_state["station_data"] = load_station_data()

    st.subheader("📊 Summary Analysis")

    summary_df = st.session_state["station_data"].copy()

    summary_df.columns = summary_df.columns.str.strip().str.lower()  # Normalize column names
    summary_df["zone"] = summary_df["zone"].astype(str).str.strip().str.lower()
    summary_df["sps_name"] = summary_df["sps_name"].astype(str).str.strip()

    for col in ["income mld", "supply mld", "pumping mld", "standby pumps"]:
        if col in summary_df.columns:
            summary_df[col] = pd.to_numeric(summary_df[col], errors="coerce").fillna(0.0)
        else:
            summary_df[col] = 0.0

    current_user = st.session_state.get("current_user", "")
    user_section = get_user_section(current_user)

    # Only restrict to own data for 'log entry' users
    if user_section == "log entry":
       summary_df = summary_df[summary_df["username"] == current_user]

    # ✅ Debug zones available
    #st.write("✅ All zones in dataset:", summary_df["zone"].unique())

    unique_zones = ["All"] + sorted(summary_df["zone"].dropna().unique())
    selected_zone_filter = st.selectbox("Filter by Zone", unique_zones)

    unique_sps = ["All"] + sorted(summary_df["sps_name"].dropna().unique())
    selected_sps = st.selectbox("Filter by SPS", unique_sps)

    st.markdown("### 📅 Select Duration or Custom Date Range")

    summary_range = st.selectbox(
        "Quick Select Duration",
        ["Today", "Yesterday", "Last 7 Days", "Last 30 Days", "This Month", "This Year", "Custom Range"]
    )

    today = date.today()

    # --- Handle Date Ranges ---
    if summary_range == "Today":
        start_date = end_date = today

    elif summary_range == "Yesterday":
        start_date = end_date = today - timedelta(days=1)

    elif summary_range == "Last 7 Days":
        start_date = today - timedelta(days=6)
        end_date = today

    elif summary_range == "Last 30 Days":
        start_date = today - timedelta(days=29)
        end_date = today

    elif summary_range == "This Month":
        start_date = today.replace(day=1)
        end_date = today

    elif summary_range == "This Year":
        start_date = today.replace(month=1, day=1)
        end_date = today

    else:  # Custom Range
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=today - timedelta(days=6))
        with col2:
            end_date = st.date_input("End Date", value=today)
        if start_date > end_date:
            st.warning("⚠️ Start Date must be before End Date.")
            st.stop()

    # --- Filter DataFrame ---
    summary_df["entry_date"] = pd.to_datetime(summary_df["entry_date"], errors='coerce')
    st.write("🕓 Data range in data:", summary_df["entry_date"].min(), "to", summary_df["entry_date"].max())

    # Filter by selected date range
    summary_df = summary_df[summary_df["entry_date"].dt.date.between(start_date, end_date)]

    # Additional zone and SPS filters
    if selected_zone_filter != "All":
        summary_df = summary_df[summary_df["zone"] == selected_zone_filter]

    if selected_sps != "All":
        summary_df = summary_df[summary_df["sps_name"] == selected_sps]
    # ------------------- ✅ ZONE GROUP SUMMARIES ---------------------
    sps_zones = {"wz", "ez", "sz", "nwz", "swz", "sr", "nz", "cz"}
    tsps_zone = {"tsps"}
    plant_zone = {"plant"}

    def zone_total(df, zone_set, fields):
        return df[df["zone"].isin(zone_set)].groupby("sps_name")[fields].sum().reset_index()

    col1, col2, col3 = st.columns(3)
    #with col1:
        #st.markdown("**📌 SPS(Pumping MLD)**")
        #sps_total = zone_total(summary_df, sps_zones, ["pumping mld"])
        #st.dataframe(sps_total)
    with col1:
        #st.markdown("**📌 SPS (Pumping MLD) Total by Zone**")

        # Filter only SPS zones from summary_df
        sps_df = summary_df[summary_df['zone'].isin(sps_zones)]

        # Group by 'zone' and sum 'pumping mld'
        sps_total = sps_df.groupby('zone')[['pumping_mld']].sum().reset_index()

        # Rename column for clarity
        sps_total = sps_total.rename(columns={'pumping_mld': 'Total Pumping MLD'})

        # Display result
        #st.dataframe(sps_total)

        # Optional: Display grand total
        grand_total = sps_total['Total Pumping MLD'].sum()
        grand_mean = sps_total['Total Pumping MLD'].mean()
        st.metric("🚰 Total SPS (Pumping MLD)", f"{grand_total:.2f}")
        st.metric("🚰 Average SPS (Pumping MLD)", f"{grand_mean:.2f}")
    #with col2:
        #st.markdown("**🏭 Plant(Income & Supply MLD)**")
        #plant_total = zone_total(summary_df, plant_zone, ["income mld", "supply mld"])
        #st.dataframe(plant_total)
    with col2:
        #st.markdown("**🏭 Plant (Income & Supply MLD) Total by Zone**")

        # Filter only Plant zones from summary_df
        plant_df = summary_df[summary_df['zone'].isin(plant_zone)]

        # Group by 'zone' and sum 'income mld' and 'supply mld'
        plant_total = plant_df.groupby('zone')[['income_mld', 'supply_mld']].sum().reset_index()

        # Rename columns for clarity (optional)
        plant_total = plant_total.rename(columns={
            'income_mld': 'Total Income MLD',
            'supply_mld': 'Total Supply MLD'
        })

        # Display result
        #st.dataframe(plant_total)

        # Optional: Show grand totals
        total_income = plant_total['Total Income MLD'].sum()
        total_supply = plant_total['Total Supply MLD'].sum()
        mean_income = plant_total['Total Income MLD'].mean()
        mean_supply = plant_total['Total Supply MLD'].mean()
        st.metric("🏭  Plant Income MLD", f"{total_income:.2f}")
        st.metric("🏭 plant Supply MLD", f"{total_supply:.2f}")
        st.metric("🏭 Average plant Income MLD", f"{mean_income:.2f}")
        st.metric("🏭 Average plant Supply MLD", f"{mean_supply:.2f}")
    #with col3:

        #st.markdown("**🌐 TSPS(Pumping MLD)**")
        #tsps_total = zone_total(summary_df, tsps_zone, ["pumping mld"])
        #st.dataframe(tsps_total)
    with col3:
        #st.markdown("**🌐 TSPS (Pumping MLD) Total by Zone**")

        # Filter only TSPS zones from summary_df
        tsps_df = summary_df[summary_df['zone'].isin(tsps_zone)]

        # Group by 'zone' and sum 'pumping mld'
        tsps_total = tsps_df.groupby('zone')[['pumping_mld']].sum().reset_index()

        # Rename column for clarity
        tsps_total = tsps_total.rename(columns={'pumping_mld': 'Total Pumping MLD'})

        # Display result
        #st.dataframe(tsps_total)

        # Optional: Display grand total
        grand_total = tsps_total['Total Pumping MLD'].sum()
        grand_mean = tsps_total['Total Pumping MLD'].mean()
        st.metric("🚰 TSPS Pumping MLD (TSPS)", f"{grand_total:.2f}")
        st.metric("🚰 Average Pumping MLD (TSPS)", f"{grand_mean:.2f}")
    # ------------------- ✅ TOTAL PER ZONE -------------------
    st.markdown("### 🌍 Total Pumping per Zone")

    # Convert to datetime (if not already)
    summary_df["entry_date"] = pd.to_datetime(summary_df["entry_date"], errors='coerce')

    # ----- 1️⃣ ZONE-WISE TOTALS -----
    zone_totals = (
        summary_df[summary_df["zone"].isin(sps_zones)]
        .groupby("zone")["pumping_mld"]
        .sum()
        .reindex(sorted(sps_zones), fill_value=0)
        .reset_index()
    )

    # ----- 2️⃣ TSPS TOTAL -----
    tsps_total = (
        summary_df[summary_df["zone"].isin(tsps_zone)]["pumping_mld"]
        .sum()
    )
    tsps_row = pd.DataFrame([{"zone": "tsps", "pumping_mld": tsps_total}])

    # ----- 3️⃣ PLANT TOTAL (income + supply) -----
    if "income_mld" in summary_df.columns and "supply_mld" in summary_df.columns:
        plant_income = summary_df[summary_df["zone"] == "plant"]["income_mld"].sum()
        plant_supply = summary_df[summary_df["zone"] == "plant"]["supply_mld"].sum()
    else:
        plant_income = 0
        plant_supply = 0

    plant_row = pd.DataFrame([{
        "zone": "plant",
        "pumping_mld": "",  # Leave blank for alignment
        "income_mld": plant_income,
        "supply_mld": plant_supply
    }])

    # ----- 4️⃣ Combine All Rows -----
    # Merge zone totals + TSPS
    final_df = pd.concat([zone_totals, tsps_row], ignore_index=True)

    # Add empty income/supply cols to all rows
    final_df["income_mld"] = ""
    final_df["supply_mld"] = ""

    # Append plant row
    final_df = pd.concat([final_df, plant_row], ignore_index=True)

    # Reorder columns
    final_df = final_df[["zone", "pumping_mld", "income_mld", "supply_mld"]]

    # ----- 5️⃣ Display -----
    st.dataframe(final_df)

    # ------------------- ✅ EXPORTS -------------------
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Log Data")
        return output.getvalue()

    user_all_df = st.session_state["station_data"].copy()
    user_all_df.columns = user_all_df.columns.str.strip().str.lower()
    if user_section == "log entry":
        user_all_df = user_all_df[user_all_df["username"] == current_user]

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 Download Filtered Data", data=to_excel(summary_df), file_name="filtered_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col2:
        st.download_button("📦 Download My Entries", data=to_excel(user_all_df), file_name="my_data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ------------------- ✅ CHARTS -------------------

    # ---------- 📊 TRENDS & VISUAL INSIGHTS ----------
    st.markdown("### 📊 Trends & Visual Insights")

    # Assuming summary_df already exists and contains columns: entry_date, zone, sps_name, pumping_mld
    filtered_chart_df = summary_df.copy()

    # Ensure 'entry_date' is in datetime format
    filtered_chart_df["entry_date"] = pd.to_datetime(filtered_chart_df["entry_date"])
    # Add a formatted version for display (if needed elsewhere)
    filtered_chart_df["entry_date_str"] = filtered_chart_df["entry_date"].dt.strftime("%d/%m/%y")

    # Chart display buttons
    show_zone_chart = st.button("📈 Show Zone-wise Trend")
    show_sps_chart = st.button("📉 Show SPS-wise Trend")
    show_combined_chart = st.button("📊 Show Combined Trend")

    # --------------------- ZONE-WISE CHART ---------------------
    if show_zone_chart:
        st.subheader("📈 Zone-wise Pumping Trend")
        zone_data = (
            filtered_chart_df
            .groupby(["entry_date", "zone"])["pumping_mld"]
            .sum()
            .reset_index()
        )

        fig_zone = px.line(
            zone_data,
            x="entry_date",
            y="pumping_mld",
            color="zone",
            title="Zone-wise Pumping Trend",
            markers=True
        )
        fig_zone.update_layout(
            xaxis_title="Date (dd/mm/yy)",
            yaxis_title="Pumping MLD",
            xaxis=dict(tickformat="%d/%m/%y"),
            yaxis=dict(tickformat=".0f")
        )
        st.plotly_chart(fig_zone, use_container_width=True)

    # --------------------- SPS-WISE CHART ---------------------
    if show_sps_chart:
        st.subheader("📉 SPS-wise Pumping Trend")
        sps_data = (
            filtered_chart_df
            .groupby(["entry_date", "sps_name"])["pumping_mld"]
            .sum()
            .reset_index()
        )

        fig_sps = px.line(
            sps_data,
            x="entry_date",
            y="pumping_mld",
            color="sps_name",
            title="SPS-wise Pumping Trend",
            markers=True
        )
        fig_sps.update_layout(
            xaxis_title="Date (dd/mm/yy)",
            yaxis_title="Pumping MLD",
            xaxis=dict(tickformat="%d/%m/%y"),
            yaxis=dict(tickformat=".0f")
        )
        st.plotly_chart(fig_sps, use_container_width=True)

    # ------------------- COMBINED CHART --------------------
    if show_combined_chart:
        st.subheader("📊 Combined Trend (Zone vs SPS)")

        # ZONE
        zone_data = (
            filtered_chart_df
            .groupby(["entry_date", "zone"])["pumping_mld"]
            .sum()
            .reset_index()
        )
        fig_combined_zone = px.line(
            zone_data,
            x="entry_date",
            y="pumping_mld",
            color="zone",
            title="Zone-wise Pumping Comparison",
            markers=True
        )
        fig_combined_zone.update_layout(
            xaxis_title="Date (dd/mm/yy)",
            yaxis_title="Pumping MLD",
            xaxis=dict(tickformat="%d/%m/%y"),
            yaxis=dict(tickformat=".0f")
        )
        st.plotly_chart(fig_combined_zone, use_container_width=True)

        # SPS
        sps_data = (
            filtered_chart_df
            .groupby(["entry_date", "sps_name"])["pumping_mld"]
            .sum()
            .reset_index()
        )
        fig_combined_sps = px.line(
            sps_data,
            x="entry_date",
            y="pumping_mld",
            color="sps_name",
            title="SPS-wise Pumping Comparison",
            markers=True
        )
        fig_combined_sps.update_layout(
            xaxis_title="Date (dd/mm/yy)",
            yaxis_title="Pumping MLD",
            xaxis=dict(tickformat="%d/%m/%y"),
            yaxis=dict(tickformat=".0f")
        )
        st.plotly_chart(fig_combined_sps, use_container_width=True)

    # ------------------- ✅ CRITICAL SPS -------------------
    st.markdown("### 🚨 Critical SPS (Standby Pumps = 0)")
    summary_df["standby pumps"] = pd.to_numeric(summary_df.get("standby pumps", 0), errors="coerce").fillna(0)
    critical_df = summary_df[summary_df["standby pumps"] == 0]
    if not critical_df.empty:
        st.dataframe(critical_df[["entry_date", "zone", "sps_name", "standby pumps"]].sort_values("entry_date", ascending=False))
        st.download_button("📥 Download Critical SPS", data=to_excel(critical_df), file_name="critical_sps.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.success("✅ No Critical SPS found.")

    # ------------------- ✅ CONTINUE WITH COMPARE DATES... -------------------
    # Keep your date comparison code unchanged; it's well-written.


