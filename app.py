import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

st.set_page_config(page_title="AICTE FDR Portal", page_icon="🏛️", layout="wide")
TODAY = date.today()


# ---------- Data ----------
def init_state():
    if "fdr" not in st.session_state:
        st.session_state.fdr = pd.DataFrame([
            ["FDR1001", "Sona College of Technology", "SBI", 500000, TODAY - timedelta(days=700), TODAY + timedelta(days=20), "Bank Verified", "None", 2, 0, ""],
            ["FDR1002", "ABC Institute of Engineering", "HDFC", 750000, TODAY - timedelta(days=900), TODAY - timedelta(days=10), "Pending", "None", 1, 0, ""],
            ["FDR1003", "XYZ College of Technology", "Canara Bank", 600000, TODAY - timedelta(days=300), TODAY + timedelta(days=400), "Bank Verified", "Requested", 3, 1, ""],
            ["FDR1004", "PQR Polytechnic", "ICICI", 400000, TODAY - timedelta(days=100), TODAY + timedelta(days=600), "Discrepancy", "None", 0, 0, "Amount mismatch"],
            ["FDR1005", "LMN School of Management", "Axis Bank", 550000, TODAY - timedelta(days=500), TODAY + timedelta(days=45), "Pending", "None", 1, 0, ""],
        ], columns=["FDR_No", "Institution", "Bank", "Amount", "Issue_Date", "Maturity_Date",
                    "Verification", "Release", "Docs", "Renewals", "Remarks"])
    if "audit" not in st.session_state:
        st.session_state.audit = [
            {"Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "User": "System",
             "Action": "Portal initialised with sample data", "FDR_No": "-"}
        ]


def log(user, action, fdr_no):
    st.session_state.audit.append({
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "User": user, "Action": action, "FDR_No": fdr_no})


def compute_status(row, alert_days):
    if row["Release"] == "Released":
        return "Released"
    days = (row["Maturity_Date"] - TODAY).days
    if days < 0:
        return "Matured"
    if days <= alert_days:
        return "Expiring"
    return "Active"


def with_status(alert_days):
    df = st.session_state.fdr.copy()
    if df.empty:
        df["Status"] = []
        df["Days_Left"] = []
        return df
    df["Status"] = df.apply(lambda r: compute_status(r, alert_days), axis=1)
    df["Days_Left"] = df["Maturity_Date"].apply(lambda d: (d - TODAY).days)
    return df


def idx_of(fdr_no):
    return st.session_state.fdr.index[st.session_state.fdr["FDR_No"] == fdr_no][0]


# ---------- Sidebar ----------
init_state()
st.sidebar.title("🏛️ AICTE FDR Portal")
role = st.sidebar.selectbox("Login as (role)", ["AICTE Officer", "Institution", "Admin"])
user = f"{role}"
alert_days = st.sidebar.slider("Reminder window (days before maturity)", 7, 180, 60)
page = st.sidebar.radio("Menu", [
    "Dashboard", "Submit FDR", "Verification", "Renewal / Replacement",
    "Release / Refund", "Alerts & Reports", "Audit Trail"])
st.sidebar.caption("Prototype • Regulation Bureau, AICTE")

df = with_status(alert_days)
is_officer = role in ("AICTE Officer", "Admin")

# ---------- Pages ----------
if page == "Dashboard":
    st.title("Security Deposit / FDR Dashboard")
    c = st.columns(6)
    c[0].metric("Total", len(df))
    for i, s in enumerate(["Active", "Expiring", "Matured", "Released"]):
        c[i + 1].metric(s, int((df["Status"] == s).sum()))
    c[5].metric("Pending verification", int((df["Verification"] == "Pending").sum()))

    st.metric("Total deposit value (₹)", f"{int(df['Amount'].sum()):,}")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Instruments by status")
        if not df.empty:
            st.bar_chart(df["Status"].value_counts())
    with col2:
        st.subheader("Verification summary")
        if not df.empty:
            st.bar_chart(df["Verification"].value_counts())

    st.subheader("Search records")
    q = st.text_input("Search by institution, bank or FDR number")
    view = df
    if q:
        mask = (df["Institution"].str.contains(q, case=False) |
                df["Bank"].str.contains(q, case=False) |
                df["FDR_No"].str.contains(q, case=False))
        view = df[mask]
    st.dataframe(view, use_container_width=True, hide_index=True)

elif page == "Submit FDR":
    st.title("Submit New FDR / Security Deposit")
    with st.form("submit_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        fdr_no = c1.text_input("FDR / Reference number")
        inst = c2.text_input("Institution name")
        bank = c1.text_input("Issuing bank")
        amount = c2.number_input("Deposit amount (₹)", min_value=0, step=10000, value=0)
        issue = c1.date_input("Issue date", value=TODAY)
        maturity = c2.date_input("Maturity date", value=TODAY + timedelta(days=365))
        files = st.file_uploader("Upload FDR document(s)", accept_multiple_files=True)
        submitted = st.form_submit_button("Submit")
    if submitted:
        fdr_no = fdr_no.strip()
        if not fdr_no or not inst.strip() or not bank.strip():
            st.error("FDR number, institution and bank are required.")
        elif fdr_no in st.session_state.fdr["FDR_No"].values:
            st.error("This FDR number already exists (possible duplicate).")
        elif amount <= 0:
            st.error("Amount must be greater than zero.")
        elif maturity <= issue:
            st.error("Maturity date must be after issue date.")
        else:
            n_docs = len(files) if files else 0
            remark = "" if n_docs else "Incomplete: no document uploaded"
            new = pd.DataFrame([[fdr_no, inst.strip(), bank.strip(), int(amount), issue, maturity,
                                 "Pending", "None", n_docs, 0, remark]],
                               columns=st.session_state.fdr.columns)
            st.session_state.fdr = pd.concat([st.session_state.fdr, new], ignore_index=True)
            log(user, "New FDR submitted (institution-declared)", fdr_no)
            st.success(f"FDR {fdr_no} submitted. Status: awaiting bank verification.")
            if not n_docs:
                st.warning("Flagged as incomplete: no supporting document.")

elif page == "Verification":
    st.title("Verification & Discrepancy Detection")
    st.caption("Institution-submitted data is kept separate from bank-confirmed data.")
    if not is_officer:
        st.warning("Only AICTE Officers/Admin can verify instruments.")
    elif df.empty:
        st.info("No records.")
    else:
        sel = st.selectbox("Select FDR", df["FDR_No"])
        row = df[df["FDR_No"] == sel].iloc[0]
        st.write(row.to_frame("Value"))
        bank_amt = st.number_input("Amount confirmed by bank (₹)", min_value=0, value=int(row["Amount"]), step=10000)
        note = st.text_input("Scrutiny observation")
        b1, b2 = st.columns(2)
        if b1.button("Run bank verification"):
            i = idx_of(sel)
            if bank_amt == int(row["Amount"]) and int(row["Docs"]) > 0:
                st.session_state.fdr.at[i, "Verification"] = "Bank Verified"
                st.session_state.fdr.at[i, "Remarks"] = note
                log(user, "Verified with bank: match", sel)
                st.success("Verified: bank data matches submitted data.")
            else:
                reason = "Amount mismatch" if bank_amt != int(row["Amount"]) else "Missing documents"
                st.session_state.fdr.at[i, "Verification"] = "Discrepancy"
                st.session_state.fdr.at[i, "Remarks"] = (note + " | " if note else "") + reason
                log(user, f"Discrepancy flagged: {reason}", sel)
                st.error(f"Discrepancy flagged: {reason}")
        if b2.button("Save observation only"):
            st.session_state.fdr.at[idx_of(sel), "Remarks"] = note
            log(user, "Scrutiny observation recorded", sel)
            st.info("Observation saved.")

elif page == "Renewal / Replacement":
    st.title("Renewal & Replacement Monitoring")
    due = df[df["Status"].isin(["Expiring", "Matured"])]
    st.subheader("Instruments needing renewal")
    st.dataframe(due, use_container_width=True, hide_index=True)
    if df.empty:
        st.info("No records.")
    else:
        sel = st.selectbox("Select FDR to renew/replace", df["FDR_No"])
        new_mat = st.date_input("New maturity date", value=TODAY + timedelta(days=365))
        if st.button("Record renewal"):
            i = idx_of(sel)
            old = st.session_state.fdr.at[i, "Maturity_Date"]
            if new_mat <= old:
                st.error("New maturity date must be later than the current one.")
            else:
                st.session_state.fdr.at[i, "Maturity_Date"] = new_mat
                st.session_state.fdr.at[i, "Renewals"] = int(st.session_state.fdr.at[i, "Renewals"]) + 1
                st.session_state.fdr.at[i, "Verification"] = "Pending"
                log(user, f"Renewed: {old} -> {new_mat}", sel)
                st.success("Renewal recorded. Re-verification required.")

elif page == "Release / Refund":
    st.title("Release / Refund Workflow")
    st.write("Flow: Institution requests → Officer approves → Release processed")
    if df.empty:
        st.info("No records.")
    else:
        sel = st.selectbox("Select FDR", df["FDR_No"])
        i = idx_of(sel)
        cur = st.session_state.fdr.at[i, "Release"]
        st.info(f"Current release status: **{cur}**")
        if cur == "None":
            if st.button("Request release (Institution)"):
                if role != "Institution" and role != "Admin":
                    st.warning("Only an institution can raise a release request.")
                else:
                    st.session_state.fdr.at[i, "Release"] = "Requested"
                    log(user, "Release requested", sel)
                    st.rerun()
        elif cur == "Requested":
            if st.button("Approve release (Officer)"):
                if not is_officer:
                    st.warning("Only an authorised officer can approve.")
                elif st.session_state.fdr.at[i, "Verification"] != "Bank Verified":
                    st.error("Cannot approve: instrument is not bank-verified.")
                else:
                    st.session_state.fdr.at[i, "Release"] = "Approved"
                    log(user, "Release approved", sel)
                    st.rerun()
        elif cur == "Approved":
            if st.button("Mark as released"):
                if not is_officer:
                    st.warning("Only an authorised officer can release.")
                else:
                    st.session_state.fdr.at[i, "Release"] = "Released"
                    log(user, "Deposit released", sel)
                    st.rerun()
        else:
            st.success("This deposit has been released.")

elif page == "Alerts & Reports":
    st.title("Alerts, Escalations & Reports")
    exp = df[df["Status"] == "Expiring"]
    mat = df[df["Status"] == "Matured"]
    pend = df[df["Verification"] == "Pending"]
    disc = df[df["Verification"] == "Discrepancy"]
    miss = df[df["Docs"] == 0]
    for _, r in mat.iterrows():
        st.error(f"🔴 OVERDUE (escalate): {r['FDR_No']} – {r['Institution']} matured {abs(r['Days_Left'])} days ago")
    for _, r in exp.iterrows():
        st.warning(f"🟠 {r['FDR_No']} – {r['Institution']} matures in {r['Days_Left']} days")
    for _, r in disc.iterrows():
        st.error(f"⚠️ Discrepancy: {r['FDR_No']} – {r['Remarks']}")
    if mat.empty and exp.empty and disc.empty:
        st.success("No urgent alerts.")
    t1, t2, t3, t4 = st.tabs(["Upcoming maturity", "Pending verification", "Missing documents", "Export"])
    with t1:
        st.dataframe(exp, use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(pend, use_container_width=True, hide_index=True)
    with t3:
        st.dataframe(miss, use_container_width=True, hide_index=True)
    with t4:
        st.download_button("Download full report (CSV)", df.to_csv(index=False).encode("utf-8"),
                           "fdr_report.csv", "text/csv")

elif page == "Audit Trail":
    st.title("Audit Trail")
    st.dataframe(pd.DataFrame(st.session_state.audit[::-1]), use_container_width=True, hide_index=True)
