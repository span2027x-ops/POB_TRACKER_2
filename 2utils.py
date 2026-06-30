import pandas as pd
import os
import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BOOKINGS_FILE = "data/bookings.xlsx"
MASTER_FILE = "data/master_data.xlsx"

BOOKING_COLUMNS = [
    "Date", "MR", "Chemist", "Product",
    "Units", "Supply Status", "Remarks"
]


def initialize_files():
    """Create data folder and seed files if they don't already exist."""
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(BOOKINGS_FILE):
        df = pd.DataFrame(columns=BOOKING_COLUMNS)
        df.to_excel(BOOKINGS_FILE, index=False)

    if not os.path.exists(MASTER_FILE):
        mr_df = pd.DataFrame({
            "MR": ["Atul", "Uvaish", "MR3", "MR4", "MR5", "MR6"]
        })

        product_df = pd.DataFrame({
            "Product": ["Activus 200", "Activus 400", "Mom 200"]
        })

        with pd.ExcelWriter(MASTER_FILE) as writer:
            mr_df.to_excel(writer, sheet_name="MR_List", index=False)
            product_df.to_excel(writer, sheet_name="Product_List", index=False)


# ---------------------------------------------------------------------------
# Master data (MR list / Product list)
# ---------------------------------------------------------------------------

def load_master_data():
    mr_df = pd.read_excel(MASTER_FILE, sheet_name="MR_List")
    product_df = pd.read_excel(MASTER_FILE, sheet_name="Product_List")

    return mr_df["MR"].dropna().tolist(), product_df["Product"].dropna().tolist()


def add_mr(name):
    mr_list, product_list = load_master_data()
    if name and name not in mr_list:
        mr_list.append(name)
        _save_master_data(mr_list, product_list)
        return True
    return False


def add_product(name):
    mr_list, product_list = load_master_data()
    if name and name not in product_list:
        product_list.append(name)
        _save_master_data(mr_list, product_list)
        return True
    return False


def remove_mr(name):
    mr_list, product_list = load_master_data()
    if name in mr_list:
        mr_list.remove(name)
        _save_master_data(mr_list, product_list)
        return True
    return False


def remove_product(name):
    mr_list, product_list = load_master_data()
    if name in product_list:
        product_list.remove(name)
        _save_master_data(mr_list, product_list)
        return True
    return False


def _save_master_data(mr_list, product_list):
    mr_df = pd.DataFrame({"MR": mr_list})
    product_df = pd.DataFrame({"Product": product_list})

    with pd.ExcelWriter(MASTER_FILE) as writer:
        mr_df.to_excel(writer, sheet_name="MR_List", index=False)
        product_df.to_excel(writer, sheet_name="Product_List", index=False)


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

def load_bookings():
    df = pd.read_excel(BOOKINGS_FILE)
    for col in BOOKING_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[BOOKING_COLUMNS]


def save_booking(entry):
    df = load_bookings()
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_excel(BOOKINGS_FILE, index=False)


def overwrite_bookings(df):
    """Persist an edited bookings dataframe back to disk."""
    df = df[BOOKING_COLUMNS]
    df.to_excel(BOOKINGS_FILE, index=False)


def delete_booking(index):
    df = load_bookings()
    if index in df.index:
        df = df.drop(index).reset_index(drop=True)
        df.to_excel(BOOKINGS_FILE, index=False)
        return True
    return False


def filter_bookings(df, mr=None, product=None, status=None, start_date=None, end_date=None):
    filtered = df.copy()

    if mr and mr != "All":
        filtered = filtered[filtered["MR"] == mr]

    if product and product != "All":
        filtered = filtered[filtered["Product"] == product]

    if status and status != "All":
        filtered = filtered[filtered["Supply Status"] == status]

    if start_date is not None and end_date is not None:
        dates = pd.to_datetime(filtered["Date"], errors="coerce")
        mask = (dates >= pd.to_datetime(start_date)) & (dates <= pd.to_datetime(end_date))
        filtered = filtered[mask]

    return filtered


def get_summary(df):
    """Return quick summary stats for the dashboard."""
    total_bookings = len(df)
    total_units = pd.to_numeric(df["Units"], errors="coerce").fillna(0).sum()
    pending = len(df[df["Supply Status"] == "Pending"])
    supplied = len(df[df["Supply Status"] == "Supplied"])

    return {
        "total_bookings": total_bookings,
        "total_units": int(total_units),
        "pending": pending,
        "supplied": supplied,
    }


# ---------------------------------------------------------------------------
# Chart-ready aggregations
# ---------------------------------------------------------------------------

def get_mr_wise_counts(df):
    """Booking counts per MR, sorted descending."""
    if df.empty:
        return pd.Series(dtype=int)
    return df.groupby("MR").size().sort_values(ascending=False)


def get_product_wise_counts(df):
    """Booking counts per Product/Brand, sorted descending."""
    if df.empty:
        return pd.Series(dtype=int)
    return df.groupby("Product").size().sort_values(ascending=False)


def get_status_counts(df):
    """Booking counts per Supply Status (for pie chart)."""
    if df.empty:
        return pd.Series(dtype=int)
    return df.groupby("Supply Status").size()


# ---------------------------------------------------------------------------
# Dashboard image export (for sharing on WhatsApp etc.)
# ---------------------------------------------------------------------------

def generate_dashboard_image(df, summary, filter_label=""):
    """
    Build a single shareable PNG image containing the summary metrics,
    MR-wise bar chart, product-wise bar chart, and status pie chart.
    Returns PNG bytes.
    """
    mr_counts = get_mr_wise_counts(df)
    product_counts = get_product_wise_counts(df)
    status_counts = get_status_counts(df)

    fig = plt.figure(figsize=(11, 9), dpi=150)
    fig.suptitle("POB Tracker - Dashboard Summary", fontsize=16, fontweight="bold")

    subtitle = filter_label if filter_label else "All Bookings"
    fig.text(0.5, 0.94, subtitle, ha="center", fontsize=10, color="gray")

    # Metrics text row
    metrics_text = (
        f"Total Bookings: {summary['total_bookings']}    |    "
        f"Total Units: {summary['total_units']}    |    "
        f"Pending: {summary['pending']}    |    "
        f"Supplied: {summary['supplied']}"
    )
    fig.text(0.5, 0.90, metrics_text, ha="center", fontsize=11)

    gs = fig.add_gridspec(2, 2, top=0.85, bottom=0.07, hspace=0.45, wspace=0.3)

    # MR-wise bar chart
    ax1 = fig.add_subplot(gs[0, 0])
    if not mr_counts.empty:
        ax1.bar(mr_counts.index.astype(str), mr_counts.values, color="#4C72B0")
        ax1.set_title("MR-wise Bookings")
        ax1.tick_params(axis="x", rotation=45)
    else:
        ax1.text(0.5, 0.5, "No data", ha="center", va="center")
        ax1.set_title("MR-wise Bookings")
        ax1.axis("off")

    # Product-wise bar chart
    ax2 = fig.add_subplot(gs[0, 1])
    if not product_counts.empty:
        ax2.bar(product_counts.index.astype(str), product_counts.values, color="#55A868")
        ax2.set_title("Product-wise Bookings")
        ax2.tick_params(axis="x", rotation=45)
    else:
        ax2.text(0.5, 0.5, "No data", ha="center", va="center")
        ax2.set_title("Product-wise Bookings")
        ax2.axis("off")

    # Supplied vs Pending pie chart
    ax3 = fig.add_subplot(gs[1, 0])
    if not status_counts.empty:
        colors_map = {"Pending": "#DD8452", "Supplied": "#55A868", "Cancelled": "#C44E52"}
        colors = [colors_map.get(s, "#8172B2") for s in status_counts.index]
        ax3.pie(
            status_counts.values,
            labels=status_counts.index,
            autopct="%1.0f%%",
            colors=colors,
            startangle=90,
        )
        ax3.set_title("Supplied vs Pending")
    else:
        ax3.text(0.5, 0.5, "No data", ha="center", va="center")
        ax3.set_title("Supplied vs Pending")
        ax3.axis("off")

    # Recent bookings mini table
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    ax4.set_title("Recent Bookings", loc="center")
    if not df.empty:
        recent = df.sort_values("Date", ascending=False).head(5)[["Date", "MR", "Product", "Supply Status"]]
        table = ax4.table(
            cellText=recent.values,
            colLabels=recent.columns,
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.4)
    else:
        ax4.text(0.5, 0.5, "No data", ha="center", va="center")

    footer = f"Generated on {datetime.now().strftime('%d-%b-%Y %I:%M %p')}"
    fig.text(0.5, 0.02, footer, ha="center", fontsize=8, color="gray")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
