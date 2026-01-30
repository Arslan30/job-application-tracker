import sys
import subprocess
from datetime import datetime, timedelta
import streamlit as st

import database  # your module-level DB functions


def run_tracker_command(args: list[str]):
    return subprocess.run(
        [sys.executable, "tracker.py"] + args,
        capture_output=True,
        text=True
    )


st.set_page_config(
    page_title="Job Application Tracker",
    layout="wide",
)

st.title("Job Application Tracker")

if st.button("Refresh data"):
    st.rerun()

# Ensure DB exists
database.init_database()

# --- Sidebar filters ---
st.sidebar.header("Filters")

status_filter = st.sidebar.selectbox(
    "Status",
    options=["(Any)", "Draft", "Applied", "Interview", "Offer", "Rejected", "Withdrawn", "Ghosted"],
    index=0
)

source_filter = st.sidebar.text_input("Source contains", value="")
company_filter = st.sidebar.text_input("Company contains", value="")
role_filter = st.sidebar.text_input("Role contains", value="")

st.sidebar.divider()

days_stale = st.sidebar.slider("Show stale applications (days since last update)", 0, 60, 14)


# --- Load data ---
apps = database.get_all_applications()
events = database.get_all_events()

# Convert to display rows
def match_filters(app: dict) -> bool:
    if status_filter != "(Any)" and (app.get("status") or "") != status_filter:
        return False
    if source_filter and source_filter.lower() not in (app.get("source") or "").lower():
        return False
    if company_filter and company_filter.lower() not in (app.get("company") or "").lower():
        return False
    if role_filter and role_filter.lower() not in (app.get("role_title") or "").lower():
        return False
    return True

filtered_apps = [a for a in apps if match_filters(a)]

# Identify stale apps
def parse_iso(dt_str: str):
    if not dt_str:
        return None
    try:
        # Handles "2026-01-30T17:12:29+01:00" etc
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None

stale_apps = []
if days_stale > 0:
    now = datetime.now()
    for a in filtered_apps:
        lu = parse_iso(a.get("last_updated_at"))
        if lu:
            delta_days = (now - lu.replace(tzinfo=None)).days
            if delta_days >= days_stale:
                stale_apps.append(a)

# --- Layout ---
col_left, col_right = st.columns([2, 1], gap="large")

with col_left:
    st.subheader("Applications")

    st.caption(f"Showing {len(filtered_apps)} applications (filtered).")

    # Build display table data
    table_rows = []
    for a in filtered_apps:
        table_rows.append({
            "ID": a.get("application_id"),
            "Status": a.get("status"),
            "Company": a.get("company"),
            "Role": a.get("role_title"),
            "Source": a.get("source"),
            "Applied": a.get("applied_date"),
            "Updated": a.get("last_updated_at"),
        })

    # Selection widget: pick by application_id
    options = ["(Select an application)"] + [r["ID"] for r in table_rows if r["ID"]]
    selected_id = st.selectbox("Select application by ID", options=options, index=0)

    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Stale applications")
    if days_stale == 0:
        st.info("Set the stale slider above to > 0 to enable stale detection.")
    elif not stale_apps:
        st.success("No stale applications under current filters.")
    else:
        st.warning(f"{len(stale_apps)} applications have not been updated in ≥ {days_stale} days.")
        st.dataframe(
            [{
                "ID": a.get("application_id"),
                "Status": a.get("status"),
                "Company": a.get("company"),
                "Role": a.get("role_title"),
                "Updated": a.get("last_updated_at"),
            } for a in stale_apps],
            use_container_width=True,
            hide_index=True
        )

with col_right:
    st.subheader("Details")

    if selected_id == "(Select an application)":
        st.info("Select an application on the left to view details and events.")
    else:
        app = database.get_application(selected_id)
        if not app:
            st.error("Application not found in DB.")
        else:
            # Read-only fields
            st.text_input("Application ID", value=app.get("application_id") or "", disabled=True)
            st.text_input("Company", value=app.get("company") or "", disabled=True)
            st.text_input("Role Title", value=app.get("role_title") or "", disabled=True)
            st.text_input("Location", value=app.get("location") or "", disabled=True)
            st.text_input("Source", value=app.get("source") or "", disabled=True)
            st.text_input("Job URL", value=app.get("job_url") or "", disabled=True)
            st.text_input("Applied Date", value=app.get("applied_date") or "", disabled=True)
            st.text_input("Last Updated", value=app.get("last_updated_at") or "", disabled=True)

            st.divider()

            # Editable fields
            new_status = st.selectbox(
                "Update Status",
                options=["Draft", "Applied", "Interview", "Offer", "Rejected", "Withdrawn", "Ghosted"],
                index=["Draft", "Applied", "Interview", "Offer", "Rejected", "Withdrawn", "Ghosted"].index(app.get("status") or "Applied")
                if (app.get("status") or "Applied") in ["Draft","Applied","Interview","Offer","Rejected","Withdrawn","Ghosted"]
                else 1
            )
            new_notes = st.text_area("Notes", value=app.get("notes") or "", height=120)
            new_followup = st.text_input("Next Follow-up Date (YYYY-MM-DD)", value=app.get("next_follow_up_date") or "")

            if st.button("Save changes", type="primary"):
                database.update_application(
                    application_id=selected_id,
                    status=new_status,
                    notes=new_notes,
                    next_follow_up_date=new_followup or None
                )
                st.success("Saved. Refresh the page if needed.")

            if st.button("Plan follow-up (+3 days)"):
                follow_date = (datetime.now().date() + timedelta(days=3)).isoformat()
                old_notes = app.get("notes") or ""
                stamp = datetime.now().date().isoformat()
                new_notes_combined = (old_notes + "\n" if old_notes else "") + f"Follow-up planned {stamp}"

                database.update_application(
                    application_id=selected_id,
                    notes=new_notes_combined,
                    next_follow_up_date=follow_date
                )
                st.success(f"Follow-up set to {follow_date}. Refresh to see changes.")

            st.divider()
            st.subheader("Events")

            app_events = [e for e in database.get_all_events() if e.get("application_id") == selected_id]
            if not app_events:
                st.caption("No events found for this application.")
            else:
                # Group by YYYY-MM-DD
                grouped = {}
                for e in app_events:
                    dt = (e.get("event_date") or "")[:10]
                    grouped.setdefault(dt, []).append(e)

                for day in sorted(grouped.keys(), reverse=True):
                    st.markdown(f"### {day}")
                    for e in grouped[day]:
                        st.write(f"**{e.get('event_type')}** — {e.get('evidence_source')}")
                        if e.get("evidence_text"):
                            st.caption(e.get("evidence_text"))

            st.divider()
            st.subheader("Add manual event")

            event_type = st.selectbox(
                "Event type",
                options=["Applied", "Interview", "Rejected", "Offer", "Other"],
                index=4
            )
            event_text = st.text_area("Evidence / Notes", value="", height=80)
            event_date = st.text_input("Event date (ISO or YYYY-MM-DD)", value=datetime.now().date().isoformat())

            if st.button("Add event"):
                database.insert_event(
                    application_id=selected_id,
                    event_type=event_type,
                    event_date=event_date,
                    evidence_source="Manual",
                    evidence_text=event_text.strip() if event_text else None
                )
                st.success("Event added. Refresh to see it.")

    st.divider()
    st.subheader("Actions")

    if st.button("Run email sync (last 7 days)"):
        result = run_tracker_command(["sync", "--since-days", "7"])
        if result.returncode != 0:
            st.error(result.stderr or result.stdout or "Sync failed")
        else:
            st.success("Email sync completed")
            if result.stdout:
                st.code(result.stdout)

    if st.button("Export Excel now"):
        result = run_tracker_command(["export", "--format", "xlsx"])
        if result.returncode != 0:
            st.error(result.stderr or result.stdout or "Export failed")
        else:
            st.success("Export completed")
            if result.stdout:
                st.code(result.stdout)
