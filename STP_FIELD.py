# Part 1: Initialization & User Auth
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import re




# ----------------- USER DATABASE ------------------
if "user_credentials" not in st.session_state:
    st.session_state.user_credentials = {
        "admin": {
            "password": "admin123",
            "section": "both",
            "registered_by": "system",
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

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
        if new_username in st.session_state.user_credentials:
            st.error("🚫 Username already exists.")
        elif new_password != confirm_password:
            st.error("❌ Passwords do not match.")
        else:
            st.session_state.user_credentials[new_username] = {
                "password": new_password,
                "section": selected_section,
                "registered_by": st.session_state.current_user or "unknown",
                "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            st.success(f"✅ User '{new_username}' created with '{selected_section}' access.")
            st.session_state.register_mode = False

# ----------------- RESET PASSWORD FORM ------------------
def reset_password_form():
    st.header("🔁 Reset Password")
    username = st.text_input("🔑 Username to Reset")
    if username not in st.session_state.user_credentials:
        st.warning("⚠️ Username does not exist.")
        return

    new_pass = st.text_input("🔐 New Password", type="password")
    confirm = st.text_input("🔐 Confirm New Password", type="password")

    if st.button("Update Password"):
        if new_pass != confirm:
            st.error("❌ Passwords do not match.")
        else:
            st.session_state.user_credentials[username]["password"] = new_pass
            st.success(f"✅ Password reset for user '{username}'.")
            st.session_state.reset_mode = False

# ----------------- DOWNLOAD REGISTERED USERS ------------------
def download_user_list():
    st.subheader("📋 Registered Users List")

    user_data = [
        {
            "Username": u,
            "Access": d["section"],
            "Registered By": d.get("registered_by", ""),
            "Registered At": d.get("registered_at", "")
        }
        for u, d in st.session_state.user_credentials.items()
    ]
    df = pd.DataFrame(user_data)

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
        creds = st.session_state.user_credentials.get(username)
        if creds and creds["password"] == password:
            allowed_section = creds["section"]
            st.session_state.logged_in = True
            st.session_state.current_user = username
            st.session_state.analysis_unlocked = allowed_section in ["analysis report", "both"]
            st.session_state.logentry_unlocked = allowed_section in ["log entry", "both"]

            # Default page setting
            if allowed_section == "log entry":
                st.session_state.active_page = "log entry"
            elif allowed_section == "analysis report":
                st.session_state.active_page = "analysis report"
            elif allowed_section == "both":
                st.session_state.active_page = "log entry"  # default page

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
user_data = st.session_state.user_credentials.get(st.session_state.current_user)

if user_data:
    st.sidebar.info(f"📄 Section Access: {user_data['section']}")
    st.sidebar.caption(f"🔐 Registered by: {user_data.get('registered_by', 'unknown')}")

    # Only for log entry access
    if user_data["section"] == "log entry":
        if st.session_state.active_page != "log entry":
            st.session_state.active_page = "log entry"
        st.sidebar.markdown("📝 Log Entry Access Only")

    # Only for analysis report access
    elif user_data["section"] == "analysis report":
        if st.session_state.active_page != "analysis report":
            st.session_state.active_page = "analysis report"
        st.sidebar.markdown("📊 Analysis Report Access Only")

    # For users with both access, show toggle button
    elif user_data["section"] == "both":
        st.sidebar.markdown("🔀 Access to Log Entry and Analysis Report")
        st.sidebar.markdown(f"📄 Currently Viewing: **{st.session_state.active_page.title()}**")
        if st.sidebar.button("🔁 Switch Page"):
            st.session_state.active_page = (
                "analysis report" if st.session_state.active_page == "log entry" else "log entry"
            )

    # Admin only button
    if st.session_state.current_user == "admin":
        if st.sidebar.button("📋 View Users"):
            st.session_state.active_page = "admin_user_list"

# Logout
if st.sidebar.button("🔓 Logout"):
    for key in [
        "logged_in", "active_page", "current_user",
        "analysis_unlocked", "logentry_unlocked",
        "register_mode", "reset_mode"
    ]:
        st.session_state[key] = False if key == "logged_in" else None
    st.rerun()


# ----------------- PAGE LOGIC ------------------
if st.session_state.active_page == "log entry":
    if not st.session_state.logentry_unlocked:
        st.error("🚫 You are not authorized to access the 'Log Entry' section.")
        st.stop()
    st.title("📝 Log Entry Page")
    st.write("Log entry form or interface goes here...")

elif st.session_state.active_page == "analysis report":
    if not st.session_state.analysis_unlocked:
        st.error("🚫 You are not authorized to access the 'Analysis Report' section.")
        st.stop()
    st.title("📊 Analysis Report Page")
    st.write("Analysis reports, filters, and charts go here...")

elif st.session_state.active_page == "admin_user_list":
    download_user_list()

# ----------------- DATA STATE ------------------
if "station_data" not in st.session_state:
    st.session_state["station_data"] = pd.DataFrame(columns=[
        "Date", "Zone", "User", "SPS Name", "Total Pumps",
        "Working Pumps", "Standby Pumps", "Standby U/M", "Remarks",
        "Pumping MLD", "Income MLD", "Supply MLD"
    ])



# ----------------- ZONE AND SPS SETUP ------------------
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



# ----------------- PAGE 1: LOG ENTRY ------------------

if st.session_state.active_page == "log entry":
    st.subheader("🗂 Select Zone")
    if "selected_zone" not in st.session_state:
        st.session_state.selected_zone = valid_zones[0]

    selected_zone = st.selectbox("Zone", valid_zones, index=valid_zones.index(st.session_state.selected_zone))
    st.session_state.selected_zone = selected_zone
    sps_options = zone_sps_map.get(selected_zone, [])

    with st.form("log_entry"):
        st.subheader("📝 Log New Entry")
        entry_date = st.date_input("Date of Entry", value=date.today())
        sps_name = st.selectbox("Name of SPS", sps_options)
        user = st.text_input("User Name or ID", value=st.session_state.get("current_user", ""))
        total_pumps = st.number_input("Total Pumps", min_value=0)
        working_pumps = st.number_input("Working Pumps", min_value=0)
        standby_pumps = st.number_input("Standby Pumps", min_value=0)
        standby_um = st.number_input("Standby Pumps U/M", min_value=0)
        remarks = st.text_area("Remarks")
        pumping_mld = st.number_input("Pumping MLD", min_value=0.0, disabled=(selected_zone == "Plant"))
        income_mld = st.number_input("Income MLD", min_value=0.0, disabled=(selected_zone != "Plant"))
        supply_mld = st.number_input("Supply MLD", min_value=0.0, disabled=(selected_zone != "Plant"))

        # 🔍 Check if an entry already exists
        existing_entry = st.session_state["station_data"][
            (st.session_state["station_data"]["Date"] == entry_date) &
            (st.session_state["station_data"]["SPS Name"] == sps_name)
        ]

        # 🔒 Block duplicate without PIN
        if not existing_entry.empty and "edit_unlocked" not in st.session_state:
            st.warning("🔒 An entry already exists for this SPS on the selected date.")
            pin = st.text_input("🔐 Enter PIN to edit existing entry", type="password")
            if st.form_submit_button("Unlock Entry"):
                if pin == "1234":  # Change this to your preferred authority PIN
                    st.session_state.edit_unlocked = True
                    st.success("✅ Edit access granted.")
                    st.rerun()
                else:
                    st.error("❌ Invalid PIN")
            st.stop()

        submitted = st.form_submit_button("Submit")

        if submitted:
            if not user.strip():
                st.warning("⚠️ Please enter your name or ID.")
            else:


                new_log = pd.DataFrame([{
                    "Date": entry_date,
                    "Zone": selected_zone,
                    "User": user,
                    "SPS Name": sps_name,
                    "Total Pumps": total_pumps,
                    "Working Pumps": working_pumps,
                    "Standby Pumps": standby_pumps,
                    "Standby U/M": standby_um,
                    "Remarks": remarks.strip(),
                    "Pumping MLD": pumping_mld if selected_zone != "Plant" else 0.0,
                    "Income MLD": income_mld if selected_zone == "Plant" else 0.0,
                    "Supply MLD": supply_mld if selected_zone == "Plant" else 0.0
                }])

                if not existing_entry.empty:
                    # Update existing row
                    index_to_update = existing_entry.index[0]
                    st.session_state["station_data"].loc[index_to_update] = new_log.values[0]
                    st.success("✏️ Entry updated successfully!")
                    st.session_state.edit_unlocked = False  # reset edit status
                else:
                    st.session_state["station_data"] = pd.concat(
                        [st.session_state["station_data"], new_log], ignore_index=True)
                    st.success("✅ Entry saved successfully!")

    if not st.session_state["station_data"].empty:
        st.subheader("📄 Recent Entries")
        current_user = st.session_state.get("current_user", "")
        recent_df = st.session_state["station_data"]
        if current_user != "admin":
            recent_df = recent_df[recent_df["User"] == current_user]
        st.dataframe(recent_df.sort_values("Date", ascending=False))

        # ----------------- PENDING SPS FOR TODAY -----------------
        st.markdown("### ⏳ Pending SPS Entries for Today")

        today = date.today()
        zone = st.session_state.selected_zone
        sps_list = zone_sps_map.get(zone, [])

        # Get today's entries for selected zone
        existing_entries = st.session_state["station_data"]
        existing_today = existing_entries[
            (pd.to_datetime(existing_entries["Date"]).dt.date == today) &
            (existing_entries["Zone"] == zone)
            ]["SPS Name"].tolist()

        # Identify pending SPS
        pending_today = [sps for sps in sps_list if sps not in existing_today]

        if pending_today:
            st.warning(f"🚧 Pending Entries for Zone **{zone}** on **{today.strftime('%d-%m-%Y')}**")
            st.dataframe(pd.DataFrame({"Pending SPS": pending_today}))
        else:
            st.success(f"✅ All SPS entries for **{zone}** are submitted for today.")



 #Part 4: Analysis Report Page
if st.session_state.active_page == "analysis report":


    st.subheader("📊 Summary Analysis")

    summary_df = st.session_state["station_data"].copy()
    current_user = st.session_state.get("current_user", "")
    if current_user != "admin":
        summary_df = summary_df[summary_df["User"] == current_user]

    unique_zones = ["All"] + sorted(summary_df["Zone"].unique())
    selected_zone_filter = st.selectbox("Filter by Zone", unique_zones)

    unique_sps = ["All"] + sorted(summary_df["SPS Name"].unique())
    selected_sps = st.selectbox("Filter by SPS", unique_sps)

    # ----------------- DATE SELECTION ------------------

    st.markdown("### 📅 Select Duration or Custom Date Range")
    summary_range = st.selectbox(
        "Quick Select Duration",
        ["Last 7 Days", "Last 30 Days", "This Month", "This Year", "Custom Range"]
    )

    today = date.today()

    if summary_range == "Last 7 Days":
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
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=today - timedelta(days=6))
        with col2:
            end_date = st.date_input("End Date", value=today)

        if start_date > end_date:
            st.warning("⚠️ Start Date must be before End Date.")
            st.stop()

    # Filter by date range
    summary_df = summary_df[pd.to_datetime(summary_df["Date"]).dt.date.between(start_date, end_date)]

    # Apply zone and SPS filters
    if selected_zone_filter != "All":
        summary_df = summary_df[summary_df["Zone"] == selected_zone_filter]
    if selected_sps != "All":
        summary_df = summary_df[summary_df["SPS Name"] == selected_sps]

    # ----------------- PENDING SPS LIST -----------------


    st.markdown("### 📊 Zone Group Summary")

    # Ensure numeric types
    summary_df["Pumping MLD"] = pd.to_numeric(summary_df["Pumping MLD"], errors="coerce").fillna(0.0)
    summary_df["Income MLD"] = pd.to_numeric(summary_df["Income MLD"], errors="coerce").fillna(0.0)
    summary_df["Supply MLD"] = pd.to_numeric(summary_df["Supply MLD"], errors="coerce").fillna(0.0)

    # Define zone groups
    sps_zones = {"WZ", "EZ", "SZ", "NWZ", "SWZ", "SR", "NZ", "CZ"}
    tsps_zone = {"TSPS"}
    plant_zone = {"Plant"}


    # ✅ Function to summarize zone totals by selected fields
    def zone_total(df, zone_set, fields):
        return df[df["Zone"].isin(zone_set)].groupby("SPS Name")[fields].sum().reset_index()


    # Layout for summary display
    col1, col2 = st.columns(2)

    # SPS zone totals
    with col1:
        st.markdown("**📌 SPS Zones Total (Pumping MLD)**")
        sps_total = zone_total(summary_df, sps_zones, ["Pumping MLD"])
        st.dataframe(sps_total)

    # Plant totals - Only Income & Supply MLD
    with col2:
        st.markdown("**🏭 Plant Total (Income & Supply MLD)**")
        plant_total = zone_total(summary_df, plant_zone, ["Income MLD", "Supply MLD"])
        st.dataframe(plant_total)

    # TSPS totals
    st.markdown("**🌐 TSPS Total (Pumping MLD)**")
    tsps_total = zone_total(summary_df, tsps_zone, ["Pumping MLD"])
    st.dataframe(tsps_total)


    # Utility: Convert DataFrame to Excel bytes
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Log Data")
        return output.getvalue()


    # Prepare data for export
    user_all_df = st.session_state["station_data"]
    if current_user != "admin":
        user_all_df = user_all_df[user_all_df["User"] == current_user]

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download Filtered Data as Excel",
                data=to_excel(summary_df),
                file_name="sps_filtered_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col2:
            st.download_button(
                label="📦 Download My Entries as Excel" if current_user != "admin" else "📦 Download All Entries as Excel",
                data=to_excel(user_all_df),
                file_name="sps_user_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No data available for selected filters.")


# ----------------- 📈 Charts & Trend Section -----------------
    st.markdown("### 📊 Trends & Visual Insights")

# Filtered data for charts
    filtered_chart_df = summary_df.copy()
    filtered_chart_df["Date"] = pd.to_datetime(filtered_chart_df["Date"])

# 🔹 Zone-wise Trend
    zone_data = filtered_chart_df.groupby(["Date", "Zone"])["Pumping MLD"].sum().reset_index()
    if not zone_data.empty:
        fig_zone = px.line(zone_data, x="Date", y="Pumping MLD", color="Zone", title="Zone-wise Pumping Trend (MLD)")
        st.plotly_chart(fig_zone, use_container_width=True)

# 🔹 SPS-wise Trend
    sps_data = filtered_chart_df.groupby(["Date", "SPS Name"])["Pumping MLD"].sum().reset_index()
    if not sps_data.empty:
        fig_sps = px.line(sps_data, x="Date", y="Pumping MLD", color="SPS Name", title="SPS-wise Pumping Trend (MLD)")
        st.plotly_chart(fig_sps, use_container_width=True)

# ----------------- 📋 Summary Table -----------------
    st.markdown("### 📋 Combined Summary Table")

    summary_table = summary_df.groupby(["Zone", "SPS Name"]).agg({
        "Pumping MLD": "sum",

    }).reset_index()

    st.dataframe(summary_table)
# ----------------- 🏭 Plant Detailed Summary -----------------
    st.markdown("### 🏭 Plant Zone Summary (Grouped)")

    plant_summary = summary_df[summary_df["Zone"] == "Plant"].groupby("SPS Name").agg({
        "Income MLD": "sum",
        "Supply MLD": "sum",
        "Date": "count"
    }).rename(columns={"Date": "Entry Count"}).reset_index()

    if not plant_summary.empty:
        st.dataframe(plant_summary)
    else:
        st.info("No data available for Plant zone in selected range.")

    # 🗓️ Today's date for default filters
    today = date.today()

    # ----------------- 🔍 Compare Metrics Between Two Dates -----------------
    st.markdown("### 🔍 Compare Metrics Between Two Dates")

    with st.form("compare_dates_form"):
        col1, col2 = st.columns(2)
        with col1:
            compare_date_1 = st.date_input("📅 First Date", value=today - timedelta(days=1), key="compare_date_1")
        with col2:
            compare_date_2 = st.date_input("📅 Second Date", value=today, key="compare_date_2")

        compare_zone = st.selectbox("🗂 Zone Filter", ["All"] + sorted(summary_df["Zone"].unique()))
        compare_sps = st.selectbox("🏭 SPS Filter", ["All"] + sorted(summary_df["SPS Name"].unique()))
        view_as_percent = st.checkbox("📉 Show as % Change", value=False)
        submitted = st.form_submit_button("Compare Dates")

    if submitted:
        df_compare = summary_df[
            pd.to_datetime(summary_df["Date"]).dt.date.isin([compare_date_1, compare_date_2])
        ]
        if compare_zone != "All":
            df_compare = df_compare[df_compare["Zone"] == compare_zone]
        if compare_sps != "All":
            df_compare = df_compare[df_compare["SPS Name"] == compare_sps]

        if df_compare.empty:
            st.warning("⚠️ No data found.")
        else:
            pivot = df_compare.pivot_table(
                index="SPS Name",
                columns=df_compare["Date"].dt.date,
                values=["Pumping MLD", "Income MLD", "Supply MLD"],
                aggfunc="sum"
            )
            pivot.columns = [f"{m} ({d})" for m, d in pivot.columns]
            pivot = pivot.reset_index()

            for metric in ["Pumping MLD", "Income MLD", "Supply MLD"]:
                col1 = f"{metric} ({compare_date_1})"
                col2 = f"{metric} ({compare_date_2})"
                if col1 in pivot.columns and col2 in pivot.columns:
                    pivot[f"\u0394 {metric}"] = pivot[col2] - pivot[col1]
                    pivot[f"% \u0394 {metric}"] = (
                            (pivot[f"\u0394 {metric}"] / pivot[col1].replace(0, float("nan"))) * 100
                    ).round(2)

            display_cols = ["SPS Name"]
            for metric in ["Pumping MLD", "Income MLD", "Supply MLD"]:
                col = f"% \u0394 {metric}" if view_as_percent else f"\u0394 {metric}"
                if col in pivot.columns:
                    display_cols.append(col)

            st.markdown(f"#### 📋 Comparison Table {'(% Change)' if view_as_percent else '(Absolute Change)'}")
            st.dataframe(pivot[display_cols].style.applymap(
                lambda v: 'color: green' if isinstance(v, (int, float)) and v > 0 else (
                    'color: red' if isinstance(v, (int, float)) and v < 0 else ''),
                subset=display_cols[1:]
            ))

            for metric in ["Pumping MLD", "Income MLD", "Supply MLD"]:
                col = f"% \u0394 {metric}" if view_as_percent else f"\u0394 {metric}"
                if col in pivot.columns:
                    chart_df = pivot[["SPS Name", col]].dropna()
                    chart_df = chart_df[chart_df[col] != 0]
                    if not chart_df.empty:
                        fig = go.Figure(go.Bar(
                            x=chart_df["SPS Name"],
                            y=chart_df[col],
                            marker_color=["green" if x > 0 else "red" for x in chart_df[col]],
                            text=chart_df[col].round(2),
                            textposition="auto"
                        ))
                        fig.update_layout(
                            title=f"📊 {metric} Change ({'%' if view_as_percent else 'MLD'}): {compare_date_1} ➜ {compare_date_2}",
                            xaxis_title="SPS Name",
                            yaxis_title=f"{metric} {'% Δ' if view_as_percent else 'Δ'}",
                            showlegend=False, height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                label=f"📥 Download {'% Change' if view_as_percent else 'Absolute Change'} Comparison",
                data=to_excel(pivot),
                file_name="date_comparison.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

#   critical SPS
    st.markdown("### 🚨 Critical SPS (Standby Pumps All in Under Maintenance)")

    if not summary_df.empty:
        critical_df = summary_df[
            summary_df["Standby Pumps"] == 0
            ]
        if not critical_df.empty:
            st.dataframe(
                critical_df[["Date", "Zone", "SPS Name", "Standby Pumps"]].sort_values("Date", ascending=False))
            st.download_button(
                label="📥 Download Critical SPS List",
                data=to_excel(critical_df),
                file_name="critical_sps_zero_standby.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ No Critical SPS ")
#  5.   for both section

if st.session_state.active_page == "Both":

    st.subheader("🗂 Select Zone")
    if "selected_zone" not in st.session_state:
        st.session_state.selected_zone = valid_zones[0]

    selected_zone = st.selectbox("Zone", valid_zones, index=valid_zones.index(st.session_state.selected_zone))
    st.session_state.selected_zone = selected_zone
    sps_options = zone_sps_map.get(selected_zone, [])

    with st.form("log_entry"):
        st.subheader("📝 Log New Entry")
        entry_date = st.date_input("Date of Entry", value=date.today())
        sps_name = st.selectbox("Name of SPS", sps_options)
        user = st.text_input("User Name or ID", value=st.session_state.get("current_user", ""))
        total_pumps = st.number_input("Total Pumps", min_value=0)
        working_pumps = st.number_input("Working Pumps", min_value=0)
        standby_pumps = st.number_input("Standby Pumps", min_value=0)
        standby_um = st.number_input("Standby Pumps U/M", min_value=0)
        remarks = st.text_area("Remarks")
        pumping_mld = st.number_input("Pumping MLD", min_value=0.0, disabled=(selected_zone == "Plant"))
        income_mld = st.number_input("Income MLD", min_value=0.0, disabled=(selected_zone != "Plant"))
        supply_mld = st.number_input("Supply MLD", min_value=0.0, disabled=(selected_zone != "Plant"))

        # 🔍 Check if an entry already exists
        existing_entry = st.session_state["station_data"][
            (st.session_state["station_data"]["Date"] == entry_date) &
            (st.session_state["station_data"]["SPS Name"] == sps_name)
        ]

        # 🔒 Block duplicate without PIN
        if not existing_entry.empty and "edit_unlocked" not in st.session_state:
            st.warning("🔒 An entry already exists for this SPS on the selected date.")
            pin = st.text_input("🔐 Enter PIN to edit existing entry", type="password")
            if st.form_submit_button("Unlock Entry"):
                if pin == "1234":  # Change this to your preferred authority PIN
                    st.session_state.edit_unlocked = True
                    st.success("✅ Edit access granted.")
                    st.rerun()
                else:
                    st.error("❌ Invalid PIN")
            st.stop()

        submitted = st.form_submit_button("Submit")

        if submitted:
            if not user.strip():
                st.warning("⚠️ Please enter your name or ID.")
            else:
                if standby_pumps == standby_um:
                    remarks = remarks + "\nNo stand by in Pumping Station"

                new_log = pd.DataFrame([{
                    "Date": entry_date,
                    "Zone": selected_zone,
                    "User": user,
                    "SPS Name": sps_name,
                    "Total Pumps": total_pumps,
                    "Working Pumps": working_pumps,
                    "Standby Pumps": standby_pumps,
                    "Standby U/M": standby_um,
                    "Remarks": remarks.strip(),
                    "Pumping MLD": pumping_mld if selected_zone != "Plant" else 0.0,
                    "Income MLD": income_mld if selected_zone == "Plant" else 0.0,
                    "Supply MLD": supply_mld if selected_zone == "Plant" else 0.0
                }])

                if not existing_entry.empty:
                    # Update existing row
                    index_to_update = existing_entry.index[0]
                    st.session_state["station_data"].loc[index_to_update] = new_log.values[0]
                    st.success("✏️ Entry updated successfully!")
                    st.session_state.edit_unlocked = False  # reset edit status
                else:
                    st.session_state["station_data"] = pd.concat(
                        [st.session_state["station_data"], new_log], ignore_index=True)
                    st.success("✅ Entry saved successfully!")

    if not st.session_state["station_data"].empty:
        st.subheader("📄 Recent Entries")
        current_user = st.session_state.get("current_user", "")
        recent_df = st.session_state["station_data"]
        if current_user != "admin":
            recent_df = recent_df[recent_df["User"] == current_user]
        st.dataframe(recent_df.sort_values("Date", ascending=False))

        # ----------------- PENDING SPS FOR TODAY -----------------
        st.markdown("### ⏳ Pending SPS Entries for Today")

        today = date.today()
        zone = st.session_state.selected_zone
        sps_list = zone_sps_map.get(zone, [])

        # Get today's entries for selected zone
        existing_entries = st.session_state["station_data"]
        existing_today = existing_entries[
            (pd.to_datetime(existing_entries["Date"]).dt.date == today) &
            (existing_entries["Zone"] == zone)
            ]["SPS Name"].tolist()

        # Identify pending SPS
        pending_today = [sps for sps in sps_list if sps not in existing_today]

        if pending_today:
            st.warning(f"🚧 Pending Entries for Zone **{zone}** on **{today.strftime('%d-%m-%Y')}**")
            st.dataframe(pd.DataFrame({"Pending SPS": pending_today}))
        else:
            st.success(f"✅ All SPS entries for **{zone}** are submitted for today.")

        # ----------------- ⚠️ Critical SPS List (Standby = Standby U/M) -----------------
        st.markdown("### 🚨 Critical SPS (Standby Pumps = Standby U/M)")

        if not summary_df.empty:
            critical_df = summary_df[summary_df["Standby Pumps"] == summary_df["Standby U/M"]]
            if not critical_df.empty:
                st.dataframe(
                    critical_df[["Date", "Zone", "SPS Name", "Standby Pumps", "Standby U/M"]].sort_values("Date",
                                                                                                          ascending=False))
                st.download_button(
                    label="📥 Download Critical SPS List",
                    data=to_excel(critical_df),
                    file_name="critical_sps_list.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.success("✅ No critical SPS found where Standby Pumps equals Standby U/M.")



 #both: Analysis Report Page

    st.subheader("📊 Summary Analysis")

    summary_df = st.session_state["station_data"].copy()
    current_user = st.session_state.get("current_user", "")
    if current_user != "admin":
        summary_df = summary_df[summary_df["User"] == current_user]

    unique_zones = ["All"] + sorted(summary_df["Zone"].unique())
    selected_zone_filter = st.selectbox("Filter by Zone", unique_zones)

    unique_sps = ["All"] + sorted(summary_df["SPS Name"].unique())
    selected_sps = st.selectbox("Filter by SPS", unique_sps)

    # ----------------- DATE SELECTION ------------------

    st.markdown("### 📅 Select Duration or Custom Date Range")
    summary_range = st.selectbox(
        "Quick Select Duration",
        ["Last 7 Days", "Last 30 Days", "This Month", "This Year", "Custom Range"]
    )

    today = date.today()

    if summary_range == "Last 7 Days":
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
    else:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=today - timedelta(days=6))
        with col2:
            end_date = st.date_input("End Date", value=today)

        if start_date > end_date:
            st.warning("⚠️ Start Date must be before End Date.")
            st.stop()

    # Filter by date range
    summary_df = summary_df[pd.to_datetime(summary_df["Date"]).dt.date.between(start_date, end_date)]

    # Apply zone and SPS filters
    if selected_zone_filter != "All":
        summary_df = summary_df[summary_df["Zone"] == selected_zone_filter]
    if selected_sps != "All":
        summary_df = summary_df[summary_df["SPS Name"] == selected_sps]

    # ----------------- PENDING SPS LIST -----------------


    st.markdown("### 📊 Zone Group Summary")

    # Ensure numeric types
    summary_df["Pumping MLD"] = pd.to_numeric(summary_df["Pumping MLD"], errors="coerce").fillna(0.0)
    summary_df["Income MLD"] = pd.to_numeric(summary_df["Income MLD"], errors="coerce").fillna(0.0)
    summary_df["Supply MLD"] = pd.to_numeric(summary_df["Supply MLD"], errors="coerce").fillna(0.0)

    # Define zone groups
    sps_zones = {"WZ", "EZ", "SZ", "NWZ", "SWZ", "SR", "NZ", "CZ"}
    tsps_zone = {"TSPS"}
    plant_zone = {"Plant"}


    # ✅ Function to summarize zone totals by selected fields
    def zone_total(df, zone_set, fields):
        return df[df["Zone"].isin(zone_set)].groupby("SPS Name")[fields].sum().reset_index()


    # Layout for summary display
    col1, col2 = st.columns(2)

    # SPS zone totals
    with col1:
        st.markdown("**📌 SPS Zones Total (Pumping MLD)**")
        sps_total = zone_total(summary_df, sps_zones, ["Pumping MLD"])
        st.dataframe(sps_total)

    # Plant totals - Only Income & Supply MLD
    with col2:
        st.markdown("**🏭 Plant Total (Income & Supply MLD)**")
        plant_total = zone_total(summary_df, plant_zone, ["Income MLD", "Supply MLD"])
        st.dataframe(plant_total)

    # TSPS totals
    st.markdown("**🌐 TSPS Total (Pumping MLD)**")
    tsps_total = zone_total(summary_df, tsps_zone, ["Pumping MLD"])
    st.dataframe(tsps_total)


    # Utility: Convert DataFrame to Excel bytes
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Log Data")
        return output.getvalue()


    # Prepare data for export
    user_all_df = st.session_state["station_data"]
    if current_user != "admin":
        user_all_df = user_all_df[user_all_df["User"] == current_user]

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download Filtered Data as Excel",
                data=to_excel(summary_df),
                file_name="sps_filtered_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col2:
            st.download_button(
                label="📦 Download My Entries as Excel" if current_user != "admin" else "📦 Download All Entries as Excel",
                data=to_excel(user_all_df),
                file_name="sps_user_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("No data available for selected filters.")


# ----------------- 📈 Charts & Trend Section -----------------
    st.markdown("### 📊 Trends & Visual Insights")

# Filtered data for charts
    filtered_chart_df = summary_df.copy()
    filtered_chart_df["Date"] = pd.to_datetime(filtered_chart_df["Date"])

# 🔹 Zone-wise Trend
    zone_data = filtered_chart_df.groupby(["Date", "Zone"])["Pumping MLD"].sum().reset_index()
    if not zone_data.empty:
        fig_zone = px.line(zone_data, x="Date", y="Pumping MLD", color="Zone", title="Zone-wise Pumping Trend (MLD)")
        st.plotly_chart(fig_zone, use_container_width=True)

# 🔹 SPS-wise Trend
    sps_data = filtered_chart_df.groupby(["Date", "SPS Name"])["Pumping MLD"].sum().reset_index()
    if not sps_data.empty:
        fig_sps = px.line(sps_data, x="Date", y="Pumping MLD", color="SPS Name", title="SPS-wise Pumping Trend (MLD)")
        st.plotly_chart(fig_sps, use_container_width=True)

# ----------------- 📋 Summary Table -----------------
    st.markdown("### 📋 Combined Summary Table")

    summary_table = summary_df.groupby(["Zone", "SPS Name"]).agg({
        "Pumping MLD": "sum",

    }).reset_index()

    st.dataframe(summary_table)
# ----------------- 🏭 Plant Detailed Summary -----------------
    st.markdown("### 🏭 Plant Zone Summary (Grouped)")

    plant_summary = summary_df[summary_df["Zone"] == "Plant"].groupby("SPS Name").agg({
        "Income MLD": "sum",
        "Supply MLD": "sum",
        "Date": "count"
    }).rename(columns={"Date": "Entry Count"}).reset_index()

    if not plant_summary.empty:
        st.dataframe(plant_summary)
    else:
        st.info("No data available for Plant zone in selected range.")

    # 🗓️ Today's date for default filters
    today = date.today()

    # ----------------- 🔍 Compare Metrics Between Two Dates -----------------
    st.markdown("### 🔍 Compare Metrics Between Two Dates")

    with st.form("compare_dates_form"):
        col1, col2 = st.columns(2)
        with col1:
            compare_date_1 = st.date_input("📅 First Date", value=today - timedelta(days=1), key="compare_date_1")
        with col2:
            compare_date_2 = st.date_input("📅 Second Date", value=today, key="compare_date_2")

        compare_zone = st.selectbox("🗂 Zone Filter", ["All"] + sorted(summary_df["Zone"].unique()))
        compare_sps = st.selectbox("🏭 SPS Filter", ["All"] + sorted(summary_df["SPS Name"].unique()))
        view_as_percent = st.checkbox("📉 Show as % Change", value=False)
        submitted = st.form_submit_button("Compare Dates")

    if submitted:
        df_compare = summary_df[
            pd.to_datetime(summary_df["Date"]).dt.date.isin([compare_date_1, compare_date_2])
        ]
        if compare_zone != "All":
            df_compare = df_compare[df_compare["Zone"] == compare_zone]
        if compare_sps != "All":
            df_compare = df_compare[df_compare["SPS Name"] == compare_sps]

        if df_compare.empty:
            st.warning("⚠️ No data found.")
        else:
            pivot = df_compare.pivot_table(
                index="SPS Name",
                columns=df_compare["Date"].dt.date,
                values=["Pumping MLD", "Income MLD", "Supply MLD"],
                aggfunc="sum"
            )
            pivot.columns = [f"{m} ({d})" for m, d in pivot.columns]
            pivot = pivot.reset_index()

            for metric in ["Pumping MLD", "Income MLD", "Supply MLD"]:
                col1 = f"{metric} ({compare_date_1})"
                col2 = f"{metric} ({compare_date_2})"
                if col1 in pivot.columns and col2 in pivot.columns:
                    pivot[f"\u0394 {metric}"] = pivot[col2] - pivot[col1]
                    pivot[f"% \u0394 {metric}"] = (
                            (pivot[f"\u0394 {metric}"] / pivot[col1].replace(0, float("nan"))) * 100
                    ).round(2)

            display_cols = ["SPS Name"]
            for metric in ["Pumping MLD", "Income MLD", "Supply MLD"]:
                col = f"% \u0394 {metric}" if view_as_percent else f"\u0394 {metric}"
                if col in pivot.columns:
                    display_cols.append(col)

            st.markdown(f"#### 📋 Comparison Table {'(% Change)' if view_as_percent else '(Absolute Change)'}")
            st.dataframe(pivot[display_cols].style.applymap(
                lambda v: 'color: green' if isinstance(v, (int, float)) and v > 0 else (
                    'color: red' if isinstance(v, (int, float)) and v < 0 else ''),
                subset=display_cols[1:]
            ))

            for metric in ["Pumping MLD", "Income MLD", "Supply MLD"]:
                col = f"% \u0394 {metric}" if view_as_percent else f"\u0394 {metric}"
                if col in pivot.columns:
                    chart_df = pivot[["SPS Name", col]].dropna()
                    chart_df = chart_df[chart_df[col] != 0]
                    if not chart_df.empty:
                        fig = go.Figure(go.Bar(
                            x=chart_df["SPS Name"],
                            y=chart_df[col],
                            marker_color=["green" if x > 0 else "red" for x in chart_df[col]],
                            text=chart_df[col].round(2),
                            textposition="auto"
                        ))
                        fig.update_layout(
                            title=f"📊 {metric} Change ({'%' if view_as_percent else 'MLD'}): {compare_date_1} ➜ {compare_date_2}",
                            xaxis_title="SPS Name",
                            yaxis_title=f"{metric} {'% Δ' if view_as_percent else 'Δ'}",
                            showlegend=False, height=400
                        )
                        st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                label=f"📥 Download {'% Change' if view_as_percent else 'Absolute Change'} Comparison",
                data=to_excel(pivot),
                file_name="date_comparison.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ----------------- ⚠️ Critical SPS List (Standby = Standby U/M) -----------------
    st.markdown("### 🚨 Critical SPS (Standby Pumps All in Under Maintenance)")

    if not summary_df.empty:
        critical_df = summary_df[
            summary_df["Standby Pumps"] == 0
            ]
        if not critical_df.empty:
            st.dataframe(
                critical_df[["Date", "Zone", "SPS Name", "Standby Pumps"]].sort_values("Date", ascending=False))
            st.download_button(
                label="📥 Download Critical SPS List",
                data=to_excel(critical_df),
                file_name="critical_sps_zero_standby.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("✅ No Critical SPS ")
