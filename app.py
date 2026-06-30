import streamlit as st
import pandas as pd
from datetime import date

from utils import (
    initialize_files,
    load_master_data,
    load_bookings,
    save_booking,
    overwrite_bookings,
    delete_booking,
    filter_bookings,
    get_summary,
    add_mr,
    add_product,
    remove_mr,
    remove_product,
    get_mr_wise_counts,
    get_product_wise_counts,
    get_status_counts,
    generate_dashboard_image,
    format_booking_label,
    ADMIN_PIN,
    BOOKING_COLUMNS,
)

st.set_page_config(
    page_title="POB Tracker",
    layout="wide"
)

initialize_files()

st.title("POB Tracker App")
st.markdown("Track daily bookings by Medical Representatives")

SUPPLY_STATUSES = ["Pending", "Supplied", "Cancelled"]

# ---------------------------------------------------------------------------
# Sidebar: who's using the app + navigation
# ---------------------------------------------------------------------------

mr_list, product_list = load_master_data()

st.sidebar.subheader("Who's logged in?")
if mr_list:
    logged_in_mr = st.sidebar.selectbox("Logged in as", mr_list, key="logged_in_mr")
else:
    logged_in_mr = None
    st.sidebar.info("Add MRs first in 'Manage Master Data'.")

admin_mode = st.sidebar.checkbox("Admin / Manager Mode")
if admin_mode:
    pin_entry = st.sidebar.text_input("Enter Admin PIN", type="password")
    is_admin = pin_entry == ADMIN_PIN
    if pin_entry and not is_admin:
        st.sidebar.error("Incorrect PIN")
else:
    is_admin = False

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "New Booking", "View / Edit Bookings", "Manage Master Data"]
)

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

if page == "Dashboard":
    df = load_bookings()

    # ---- Quick "New Booking" button at the very top ----
    with st.expander("➕ New Booking", expanded=False):
        if not mr_list or not product_list:
            st.warning("Please add at least one MR and one Product in 'Manage Master Data' before creating a booking.")
        else:
            with st.form("quick_booking_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    q_date = st.date_input("Date", value=date.today(), key="q_date")
                    q_mr = st.selectbox(
                        "MR", mr_list,
                        index=mr_list.index(logged_in_mr) if logged_in_mr in mr_list else 0,
                        key="q_mr",
                    )
                    q_chemist = st.text_input("Chemist", key="q_chemist")
                with c2:
                    q_product = st.selectbox("Product", product_list, key="q_product")
                    q_units = st.number_input("Units", min_value=1, step=1, value=1, key="q_units")
                    q_status = st.selectbox("Supply Status", SUPPLY_STATUSES, key="q_status")

                q_remarks = st.text_area("Remarks", placeholder="Optional notes...", key="q_remarks")

                q_submitted = st.form_submit_button("Save Booking")

                if q_submitted:
                    if not q_chemist.strip():
                        st.error("Chemist name cannot be empty.")
                    else:
                        entry = {
                            "Date": q_date.strftime("%Y-%m-%d"),
                            "MR": q_mr,
                            "Chemist": q_chemist.strip(),
                            "Product": q_product,
                            "Units": int(q_units),
                            "Supply Status": q_status,
                            "Remarks": q_remarks.strip(),
                        }
                        save_booking(entry)
                        st.success(f"Booking saved for {q_mr} - {q_chemist} ({q_product})")
                        st.rerun()

    st.divider()

    # ---- Dashboard summary right below the New Booking button ----
    st.subheader("Filters")
    d1, d2, d3, d4 = st.columns(4)
    with d1:
        dash_mr = st.selectbox("MR", ["All"] + mr_list, key="dash_mr")
    with d2:
        dash_product = st.selectbox("Brand / Product", ["All"] + product_list, key="dash_product")
    with d3:
        dash_start = st.date_input("From", value=None, key="dash_start")
    with d4:
        dash_end = st.date_input("To", value=None, key="dash_end")

    filtered = filter_bookings(
        df,
        mr=dash_mr,
        product=dash_product,
        start_date=dash_start if dash_start else None,
        end_date=dash_end if dash_end else None,
    )

    filter_bits = []
    if dash_mr != "All":
        filter_bits.append(f"MR: {dash_mr}")
    if dash_product != "All":
        filter_bits.append(f"Brand: {dash_product}")
    if dash_start and dash_end:
        filter_bits.append(f"{dash_start} to {dash_end}")
    filter_label = " | ".join(filter_bits) if filter_bits else "All Bookings"

    st.caption(f"Showing {len(filtered)} of {len(df)} bookings — {filter_label}")

    summary = get_summary(filtered)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Bookings", summary["total_bookings"])
    col2.metric("Total Units", summary["total_units"])
    col3.metric("Pending", summary["pending"])
    col4.metric("Supplied", summary["supplied"])

    st.divider()

    if filtered.empty:
        st.info("No bookings match the selected filters yet.")
    else:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("**MR-wise Booking Numbers**")
            mr_counts = get_mr_wise_counts(filtered)
            st.bar_chart(mr_counts)

        with chart_col2:
            st.markdown("**Product-wise Booking Numbers**")
            product_counts = get_product_wise_counts(filtered)
            st.bar_chart(product_counts)

        chart_col3, chart_col4 = st.columns(2)

        with chart_col3:
            st.markdown("**Supplied vs Pending**")
            status_counts = get_status_counts(filtered)
            status_df = status_counts.reset_index()
            status_df.columns = ["Supply Status", "Count"]
            st.bar_chart(status_df.set_index("Supply Status"))
            st.dataframe(status_df, use_container_width=True, hide_index=True)

        with chart_col4:
            st.markdown("**Status Breakdown (Pie)**")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            colors_map = {"Pending": "#DD8452", "Supplied": "#55A868", "Cancelled": "#C44E52"}
            colors = [colors_map.get(s, "#8172B2") for s in status_counts.index]
            ax.pie(status_counts.values, labels=status_counts.index, autopct="%1.0f%%", colors=colors, startangle=90)
            ax.axis("equal")
            st.pyplot(fig)

        st.divider()
        st.subheader("Recent Bookings")
        st.dataframe(filtered.sort_values("Date", ascending=False).head(10), use_container_width=True)

        st.divider()
        st.subheader("Share Dashboard")
        st.caption("Download a snapshot image of this dashboard to share on WhatsApp or elsewhere.")
        image_bytes = generate_dashboard_image(filtered, summary, filter_label)
        st.image(image_bytes, caption="Preview of shareable dashboard image", use_container_width=True)
        st.download_button(
            "📤 Download Dashboard Image (PNG)",
            data=image_bytes,
            file_name="pob_dashboard_summary.png",
            mime="image/png",
        )

# ---------------------------------------------------------------------------
# New Booking
# ---------------------------------------------------------------------------

elif page == "New Booking":
    st.subheader("Add a New Booking")

    if not mr_list or not product_list:
        st.warning("Please add at least one MR and one Product in 'Manage Master Data' before creating a booking.")
    else:
        with st.form("booking_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                booking_date = st.date_input("Date", value=date.today())
                mr = st.selectbox("MR", mr_list)
                chemist = st.text_input("Chemist")
            with c2:
                product = st.selectbox("Product", product_list)
                units = st.number_input("Units", min_value=1, step=1, value=1)
                supply_status = st.selectbox("Supply Status", SUPPLY_STATUSES)

            remarks = st.text_area("Remarks", placeholder="Optional notes...")

            submitted = st.form_submit_button("Save Booking")

            if submitted:
                if not chemist.strip():
                    st.error("Chemist name cannot be empty.")
                else:
                    entry = {
                        "Date": booking_date.strftime("%Y-%m-%d"),
                        "MR": mr,
                        "Chemist": chemist.strip(),
                        "Product": product,
                        "Units": int(units),
                        "Supply Status": supply_status,
                        "Remarks": remarks.strip(),
                    }
                    save_booking(entry)
                    st.success(f"Booking saved for {mr} - {chemist} ({product})")

# ---------------------------------------------------------------------------
# View / Edit Bookings
# ---------------------------------------------------------------------------

elif page == "View / Edit Bookings":
    st.subheader("View & Filter Bookings")

    if not is_admin:
        st.info(f"You're viewing and editing only **{logged_in_mr}'s** bookings. "
                f"Switch to Admin / Manager Mode (sidebar) to manage everyone's data.")

    df = load_bookings()

    # Restrict to the logged-in MR's own rows unless Admin Mode is active
    if not is_admin and logged_in_mr:
        df = df[df["MR"] == logged_in_mr]

    f1, f2, f3, f4, f5 = st.columns(5)
    with f1:
        mr_options = ["All"] + mr_list if is_admin else [logged_in_mr]
        mr_filter = st.selectbox("Filter by MR", mr_options, disabled=not is_admin)
    with f2:
        product_filter = st.selectbox("Filter by Product", ["All"] + product_list)
    with f3:
        status_filter = st.selectbox("Filter by Status", ["All"] + SUPPLY_STATUSES)
    with f4:
        start_date = st.date_input("From", value=None, key="start_date")
    with f5:
        end_date = st.date_input("To", value=None, key="end_date")

    filtered = filter_bookings(
        df,
        mr=mr_filter,
        product=product_filter,
        status=status_filter,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
    )

    st.caption(f"Showing {len(filtered)} of {len(df)} bookings")

    if filtered.empty:
        st.info("No bookings match the selected filters.")
    else:
        edited_df = st.data_editor(
            filtered,
            use_container_width=True,
            num_rows="fixed",  # prevents accidental row deletion via the table's trash icon
            disabled=["MR"] if not is_admin else [],
            key="bookings_editor",
        )

        col_a, col_b = st.columns([1, 4])
        with col_a:
            if st.button("Save Changes"):
                # Merge edited rows back into the full (unfiltered) dataset
                full_df = load_bookings()
                full_df.loc[edited_df.index] = edited_df
                overwrite_bookings(full_df)
                st.success("Changes saved.")

        with col_b:
            st.download_button(
                "Download as Excel",
                data=filtered.to_csv(index=False).encode("utf-8"),
                file_name="bookings_export.csv",
                mime="text/csv",
            )

    st.divider()
    st.subheader("Delete a Booking")

    if filtered.empty:
        st.caption("No bookings available to delete.")
    else:
        options = {
            format_booking_label(idx, row): idx
            for idx, row in filtered.iterrows()
        }
        selected_label = st.selectbox("Select the exact booking to delete", list(options.keys()))
        selected_index = options[selected_label]

        st.warning(f"You are about to delete: **{selected_label}**")
        confirm = st.checkbox("Yes, I'm sure I want to delete this booking.")

        if st.button("Delete Booking", type="primary", disabled=not confirm):
            if delete_booking(int(selected_index)):
                st.success("Booking deleted.")
                st.rerun()
            else:
                st.error("Could not delete that row — it may have already been removed.")

# ---------------------------------------------------------------------------
# Manage Master Data
# ---------------------------------------------------------------------------

elif page == "Manage Master Data":
    st.subheader("Manage Medical Representatives")

    c1, c2 = st.columns(2)
    with c1:
        new_mr = st.text_input("Add new MR")
        if st.button("Add MR"):
            if add_mr(new_mr.strip()):
                st.success(f"Added MR: {new_mr}")
                st.rerun()
            else:
                st.warning("MR name is empty or already exists.")

    with c2:
        if mr_list:
            mr_to_remove = st.selectbox("Remove MR", mr_list, key="remove_mr_select")
            if st.button("Remove MR"):
                remove_mr(mr_to_remove)
                st.success(f"Removed MR: {mr_to_remove}")
                st.rerun()

    st.divider()
    st.subheader("Manage Products")

    c3, c4 = st.columns(2)
    with c3:
        new_product = st.text_input("Add new Product")
        if st.button("Add Product"):
            if add_product(new_product.strip()):
                st.success(f"Added Product: {new_product}")
                st.rerun()
            else:
                st.warning("Product name is empty or already exists.")

    with c4:
        if product_list:
            product_to_remove = st.selectbox("Remove Product", product_list, key="remove_product_select")
            if st.button("Remove Product"):
                remove_product(product_to_remove)
                st.success(f"Removed Product: {product_to_remove}")
                st.rerun()

    st.divider()
    st.subheader("Current Master Data")
    mc1, mc2 = st.columns(2)
    with mc1:
        st.write("**MR List**")
        st.dataframe(pd.DataFrame({"MR": mr_list}), use_container_width=True)
    with mc2:
        st.write("**Product List**")
        st.dataframe(pd.DataFrame({"Product": product_list}), use_container_width=True)
