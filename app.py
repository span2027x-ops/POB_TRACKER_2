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
# Sidebar navigation
# ---------------------------------------------------------------------------

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "New Booking", "View / Edit Bookings", "Manage Master Data"]
)

mr_list, product_list = load_master_data()

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

if page == "Dashboard":
    df = load_bookings()

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

    df = load_bookings()

    f1, f2, f3, f4, f5 = st.columns(5)
    with f1:
        mr_filter = st.selectbox("Filter by MR", ["All"] + mr_list)
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
            num_rows="dynamic",
            key="bookings_editor",
        )

        col_a, col_b = st.columns([1, 4])
        with col_a:
            if st.button("Save Changes"):
                # Merge edited rows back into the full dataset
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
    if not df.empty:
        row_to_delete = st.number_input(
            "Row index to delete (see table above)",
            min_value=0,
            max_value=max(len(df) - 1, 0),
            step=1,
        )
        if st.button("Delete Row", type="primary"):
            if delete_booking(int(row_to_delete)):
                st.success(f"Row {row_to_delete} deleted.")
                st.rerun()
            else:
                st.error("Could not delete that row.")

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
