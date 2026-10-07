import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

# ⚠️ set_page_config phải là lệnh Streamlit ĐẦU TIÊN
st.set_page_config(page_title="Công Cụ Tính Lãi Tiết Kiệm", page_icon="💰", layout="wide")

# ----------------------------------------------------------------------------
# HÀM TIỆN ÍCH
# ----------------------------------------------------------------------------
SIMPLE_MODES = ["Hàng tháng", "Hàng quý", "Cuối kỳ"]
COMPOUND_MODES = ["Hàng tháng", "Hàng quý", "Hàng năm"]
STEP_MONTHS = {"Hàng tháng": 1, "Hàng quý": 3, "Hàng năm": 12, "Cuối kỳ": 12}
TERM_PRESETS = [1, 3, 6, 9, 12, 13, 18, 24, 36, 60, "Tùy chỉnh"]


def fmt_vnd(v: float) -> str:
    return f"{v:,.0f} VNĐ"


def fmt_short(v: float) -> str:
    """Rút gọn tiền: 1.500.000.000 -> 1,50 tỷ"""
    if v >= 1e9:
        return f"≈ {v / 1e9:,.2f} tỷ đồng"
    if v >= 1e6:
        return f"≈ {v / 1e6:,.1f} triệu đồng"
    return f"{v:,.0f} đồng"


def ear(principal: float, total: float, months: int) -> float:
    """Lãi suất thực tế quy đổi theo năm (%)."""
    if principal <= 0 or months <= 0 or total <= 0:
        return 0.0
    return ((total / principal) ** (12 / months) - 1) * 100


def add_months(start: date, months: int) -> pd.Timestamp:
    return pd.Timestamp(start) + pd.DateOffset(months=int(months))


def to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")  # utf-8-sig để Excel đọc đúng tiếng Việt


def schedule(principal, rate_pct, months, kind, mode, start=None) -> pd.DataFrame:
    """Bảng diễn biến theo từng tháng."""
    r = rate_pct / 100
    rows, prev = [], principal
    for m in range(0, months + 1):
        if kind == "Lãi đơn":
            bal = principal * (1 + r * m / 12)
        else:  # Lãi kép: gộp lãi theo từng kỳ, phần lẻ tính lãi đơn theo thời gian
            k = STEP_MONTHS.get(mode, 12)
            done = m // k
            base = principal * (1 + r * k / 12) ** done
            bal = base * (1 + r * (m - done * k) / 12)
        row = {
            "Tháng": m,
            "Lãi phát sinh": bal - prev if m > 0 else 0.0,
            "Lãi lũy kế": bal - principal,
            "Tổng giá trị": bal,
        }
        if start is not None:
            row = {"Ngày": add_months(start, m).strftime("%d/%m/%Y"), **row}
        rows.append(row)
        prev = bal
    return pd.DataFrame(rows)


def style_money(df: pd.DataFrame):
    money_cols = [c for c in df.columns if c not in ("Tháng", "Ngày", "Năm")]
    return df.style.format("{:,.0f}", subset=money_cols)


def save_history(entry: dict):
    st.session_state.setdefault("history", [])
    entry["Thời điểm"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    st.session_state["history"].insert(0, entry)


# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
with st.sidebar:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg")
    st.header("⚙️ Thiết lập chung")
    inflation = st.number_input(
        "Lạm phát dự kiến (%/năm)", min_value=0.0, max_value=50.0, value=3.5, step=0.1,
        help="Dùng để quy đổi ra sức mua thực tế của số tiền nhận được.",
    )
    st.markdown("---")
    st.caption(
        "💡 Kết quả chỉ mang tính tham khảo. Cách tính lãi thực tế phụ thuộc quy định "
        "từng ngân hàng (số ngày/năm, làm tròn, điều kiện tái tục...)."
    )

st.title("💰 Công Cụ Tính Lãi Tiết Kiệm")
st.caption("Thực hiện bởi: **Lê Hoàng Minh Thư**")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "🧮 Tính lãi",
        "⚖️ So sánh",
        "📅 Gửi góp hàng tháng",
        "🎯 Mục tiêu tiết kiệm",
        "🚨 Rút trước hạn",
        "🕘 Lịch sử",
    ]
)

# ----------------------------------------------------------------------------
# TAB 1: TÍNH LÃI
# ----------------------------------------------------------------------------
with tab1:
    st.subheader("Tính lãi tiền gửi có kỳ hạn")
    c1, c2, c3 = st.columns(3)

    with c1:
        principal = st.number_input("Số tiền gửi (VNĐ):", min_value=0, value=100_000_000,
                                    step=1_000_000, format="%d", key="t1_principal")
        st.caption(fmt_short(principal))
        interest_rate = st.number_input("Lãi suất (%/năm):", min_value=0.0, value=6.0,
                                        step=0.1, format="%.2f", key="t1_rate")
    with c2:
        preset = st.selectbox("Kỳ hạn gửi (tháng):", TERM_PRESETS, index=4, key="t1_preset")
        if preset == "Tùy chỉnh":
            term_months = st.number_input("Nhập số tháng:", min_value=1, max_value=600,
                                          value=15, step=1, key="t1_term")
        else:
            term_months = int(preset)
        start_date = st.date_input("Ngày gửi:", value=date.today(), format="DD/MM/YYYY", key="t1_start")
    with c3:
        interest_type = st.selectbox("Phương pháp tính lãi:", ["Lãi đơn", "Lãi kép"], key="t1_type")
        if interest_type == "Lãi đơn":
            payout_method = st.selectbox("Hình thức lãnh lãi:", SIMPLE_MODES, index=2, key="t1_mode_s")
        else:
            payout_method = st.selectbox("Kỳ ghép lãi (nhập gốc):", COMPOUND_MODES, key="t1_mode_c")

    if interest_type == "Lãi kép" and term_months % STEP_MONTHS[payout_method] != 0:
        st.warning("⚠️ Kỳ hạn không chia hết cho kỳ ghép lãi. Phần dư cuối kỳ được tính lãi đơn theo tỷ lệ thời gian.")

    df = schedule(principal, interest_rate, term_months, interest_type, payout_method, start_date)
    total_amount = df["Tổng giá trị"].iloc[-1]
    total_interest = df["Lãi lũy kế"].iloc[-1]
    maturity = add_months(start_date, term_months)

    # Lãi định kỳ
    if interest_type == "Lãi đơn" and payout_method == "Hàng tháng":
        periodic_label, periodic_val = "Tiền lãi nhận hàng tháng", fmt_vnd(principal * interest_rate / 100 / 12)
    elif interest_type == "Lãi đơn" and payout_method == "Hàng quý":
        periodic_label, periodic_val = "Tiền lãi nhận hàng quý", fmt_vnd(principal * interest_rate / 100 / 4)
    elif interest_type == "Lãi kép":
        periodic_label, periodic_val = "Tiền lãi định kỳ", "Nhập gốc 🔄"
    else:
        periodic_label, periodic_val = "Tiền lãi định kỳ", "0 VNĐ (nhận cuối kỳ)"

    st.markdown("### 📊 Kết quả")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(periodic_label, periodic_val)
    m2.metric("Tổng tiền lãi", fmt_vnd(total_interest), help=fmt_short(total_interest))
    m3.metric("Tổng gốc + lãi", fmt_vnd(total_amount), help=fmt_short(total_amount))
    m4.metric("Lãi suất thực tế/năm", f"{ear(principal, total_amount, term_months):.2f}%")

    n1, n2, n3 = st.columns(3)
    n1.metric("📅 Ngày đáo hạn", maturity.strftime("%d/%m/%Y"))
    n2.metric("Lãi bình quân/tháng", fmt_vnd(total_interest / term_months))
    real_value = total_amount / ((1 + inflation / 100) ** (term_months / 12))
    n3.metric("Sức mua thực tế (sau lạm phát)", fmt_vnd(real_value),
              delta=f"{real_value - principal:,.0f} VNĐ so với gốc")

    if real_value < principal:
        st.error(f"📉 Với lạm phát {inflation:.1f}%/năm, lãi suất này chưa đủ bù trượt giá: sức mua giảm.")
    else:
        st.success(f"📈 Sau lạm phát {inflation:.1f}%/năm, bạn vẫn tăng được sức mua thực tế.")

    st.markdown("#### 📈 Diễn biến giá trị tiền gửi")
    st.line_chart(df.set_index("Tháng")[["Tổng giá trị", "Lãi lũy kế"]])

    with st.expander("📋 Bảng chi tiết theo tháng"):
        st.dataframe(style_money(df), width="stretch", hide_index=True)
        st.download_button("⬇️ Tải bảng (CSV)", to_csv(df), "bang_tinh_lai.csv", "text/csv")

    if st.button("💾 Lưu vào lịch sử", key="t1_save"):
        save_history({
            "Số tiền gửi": principal, "Lãi suất %": interest_rate, "Kỳ hạn (tháng)": term_months,
            "Loại lãi": f"{interest_type} - {payout_method}",
            "Tổng lãi": round(total_interest), "Tổng nhận": round(total_amount),
        })
        st.toast("Đã lưu vào lịch sử!", icon="✅")

# ----------------------------------------------------------------------------
# TAB 2: SO SÁNH
# ----------------------------------------------------------------------------
with tab2:
    st.subheader("So sánh nhiều gói gửi / nhiều ngân hàng")
    st.caption("Sửa trực tiếp trong bảng, bấm dấu + ở cuối bảng để thêm gói mới.")
    cmp_principal = st.number_input("Số tiền gửi để so sánh (VNĐ):", min_value=0, value=100_000_000,
                                    step=1_000_000, format="%d", key="t2_principal")

    default_df = pd.DataFrame([
        {"Tên gói": "Ngân hàng A", "Lãi suất (%/năm)": 5.5, "Kỳ hạn (tháng)": 12, "Loại lãi": "Lãi đơn", "Kỳ lãi / ghép": "Cuối kỳ"},
        {"Tên gói": "Ngân hàng B", "Lãi suất (%/năm)": 5.8, "Kỳ hạn (tháng)": 12, "Loại lãi": "Lãi kép", "Kỳ lãi / ghép": "Hàng tháng"},
        {"Tên gói": "Ngân hàng C", "Lãi suất (%/năm)": 6.2, "Kỳ hạn (tháng)": 24, "Loại lãi": "Lãi đơn", "Kỳ lãi / ghép": "Cuối kỳ"},
    ])
    edited = st.data_editor(
        default_df, num_rows="dynamic", width="stretch", key="t2_editor",
        column_config={
            "Lãi suất (%/năm)": st.column_config.NumberColumn(min_value=0.0, max_value=30.0, step=0.1, format="%.2f"),
            "Kỳ hạn (tháng)": st.column_config.NumberColumn(min_value=1, max_value=600, step=1, format="%d"),
            "Loại lãi": st.column_config.SelectboxColumn(options=["Lãi đơn", "Lãi kép"]),
            "Kỳ lãi / ghép": st.column_config.SelectboxColumn(options=["Hàng tháng", "Hàng quý", "Hàng năm", "Cuối kỳ"]),
        },
    )

    valid = edited.dropna()
    results = []
    for _, row in valid.iterrows():
        months = int(row["Kỳ hạn (tháng)"])
        d = schedule(cmp_principal, float(row["Lãi suất (%/năm)"]), months, row["Loại lãi"], row["Kỳ lãi / ghép"])
        tot = d["Tổng giá trị"].iloc[-1]
        results.append({
            "Tên gói": row["Tên gói"],
            "Kỳ hạn (tháng)": months,
            "Tổng lãi": tot - cmp_principal,
            "Tổng nhận": tot,
            "Lãi suất thực tế/năm (%)": ear(cmp_principal, tot, months),
        })

    if results:
        res_df = pd.DataFrame(results).sort_values("Lãi suất thực tế/năm (%)", ascending=False)
        best = res_df.iloc[0]
        st.success(f"🏆 Hiệu quả nhất theo năm: **{best['Tên gói']}** — lãi suất thực tế "
                   f"**{best['Lãi suất thực tế/năm (%)']:.2f}%/năm**, nhận {fmt_vnd(best['Tổng lãi'])} tiền lãi.")
        st.dataframe(
            res_df.style.format({"Tổng lãi": "{:,.0f}", "Tổng nhận": "{:,.0f}",
                                 "Lãi suất thực tế/năm (%)": "{:.2f}"}),
            width="stretch", hide_index=True,
        )
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**Tổng tiền lãi nhận được**")
            st.bar_chart(res_df.set_index("Tên gói")["Tổng lãi"])
        with cc2:
            st.markdown("**Lãi suất thực tế/năm (%)**")
            st.bar_chart(res_df.set_index("Tên gói")["Lãi suất thực tế/năm (%)"])
        st.caption("Các gói có kỳ hạn khác nhau nên so sánh bằng *lãi suất thực tế/năm*, không phải tổng lãi.")
    else:
        st.info("Hãy nhập ít nhất một gói hợp lệ.")

# ----------------------------------------------------------------------------
# TAB 3: GỬI GÓP HÀNG THÁNG
# ----------------------------------------------------------------------------
with tab3:
    st.subheader("Gửi góp hàng tháng (tích lũy dần)")
    g1, g2, g3 = st.columns(3)
    with g1:
        initial3 = st.number_input("Số tiền ban đầu (VNĐ):", min_value=0, value=0, step=1_000_000,
                                   format="%d", key="t3_init")
        monthly3 = st.number_input("Gửi thêm mỗi tháng (VNĐ):", min_value=0, value=5_000_000,
                                   step=500_000, format="%d", key="t3_monthly")
    with g2:
        rate3 = st.number_input("Lãi suất (%/năm):", min_value=0.0, value=6.0, step=0.1,
                                format="%.2f", key="t3_rate")
        years3 = st.number_input("Thời gian (năm):", min_value=1, max_value=50, value=5, step=1, key="t3_years")
    with g3:
        raise3 = st.number_input("Mỗi năm tăng số tiền gửi thêm (%):", min_value=0.0, max_value=100.0,
                                 value=0.0, step=1.0, key="t3_raise",
                                 help="Ví dụ lương tăng 10%/năm thì khoản gửi cũng tăng 10%/năm.")
        st.caption("Giả định: gửi vào đầu mỗi tháng, lãi nhập gốc hàng tháng.")

    i3 = rate3 / 100 / 12
    bal, contributed = float(initial3), float(initial3)
    rows3 = [{"Tháng": 0, "Tổng đã gửi": contributed, "Giá trị tài khoản": bal, "Lãi": 0.0}]
    for m in range(1, int(years3) * 12 + 1):
        dep = monthly3 * (1 + raise3 / 100) ** ((m - 1) // 12)
        bal = (bal + dep) * (1 + i3)
        contributed += dep
        rows3.append({"Tháng": m, "Tổng đã gửi": contributed, "Giá trị tài khoản": bal, "Lãi": bal - contributed})
    df3 = pd.DataFrame(rows3)

    k1, k2, k3 = st.columns(3)
    k1.metric("Tổng tiền đã gửi", fmt_vnd(contributed))
    k2.metric("Tổng tiền lãi", fmt_vnd(bal - contributed))
    k3.metric("Số dư cuối kỳ", fmt_vnd(bal), help=fmt_short(bal))

    st.line_chart(df3.set_index("Tháng")[["Tổng đã gửi", "Giá trị tài khoản"]])
    with st.expander("📋 Bảng chi tiết"):
        st.dataframe(style_money(df3), width="stretch", hide_index=True)
        st.download_button("⬇️ Tải bảng (CSV)", to_csv(df3), "gui_gop_hang_thang.csv", "text/csv")

# ----------------------------------------------------------------------------
# TAB 4: MỤC TIÊU TIẾT KIỆM
# ----------------------------------------------------------------------------
with tab4:
    st.subheader("Lập kế hoạch đạt mục tiêu tiết kiệm")
    goal_mode = st.radio("Bạn muốn biết điều gì?",
                         ["Cần gửi bao nhiêu mỗi tháng?", "Bao lâu thì đạt mục tiêu?"], horizontal=True)
    a1, a2 = st.columns(2)
    with a1:
        target = st.number_input("Mục tiêu (VNĐ):", min_value=1_000_000, value=1_000_000_000,
                                 step=10_000_000, format="%d", key="t4_target")
        st.caption(fmt_short(target))
        init4 = st.number_input("Đã có sẵn (VNĐ):", min_value=0, value=50_000_000,
                                step=1_000_000, format="%d", key="t4_init")
    with a2:
        rate4 = st.number_input("Lãi suất kỳ vọng (%/năm):", min_value=0.0, value=6.0, step=0.1,
                                format="%.2f", key="t4_rate")
        i4 = rate4 / 100 / 12
        if goal_mode.startswith("Cần"):
            years4 = st.number_input("Muốn đạt trong (năm):", min_value=1, max_value=50, value=10, step=1, key="t4_years")
        else:
            monthly4 = st.number_input("Khả năng gửi mỗi tháng (VNĐ):", min_value=0, value=8_000_000,
                                       step=500_000, format="%d", key="t4_monthly")

    if goal_mode.startswith("Cần"):
        n = int(years4) * 12
        growth = (1 + i4) ** n
        fv_init = init4 * growth
        annuity = n if i4 == 0 else ((growth - 1) / i4) * (1 + i4)
        need = max(0.0, (target - fv_init) / annuity)
        if need == 0:
            st.success("🎉 Chỉ với số tiền đang có, bạn đã đạt mục tiêu mà không cần gửi thêm.")
        else:
            st.metric("Số tiền cần gửi mỗi tháng", fmt_vnd(need), help=fmt_short(need))
            total_in = init4 + need * n
            st.write(f"Tổng bạn bỏ ra: **{fmt_vnd(total_in)}** — tiền lãi sinh ra: **{fmt_vnd(target - total_in)}**.")
        monthly_used, n_used = need, n
    else:
        bal, m = float(init4), 0
        while bal < target and m < 1200:
            bal = (bal + monthly4) * (1 + i4)
            m += 1
        if bal < target:
            st.error("Với mức gửi này bạn không đạt mục tiêu trong 100 năm. Hãy tăng số tiền gửi hoặc lãi suất.")
            monthly_used, n_used = monthly4, 0
        else:
            st.metric("Thời gian cần thiết", f"{m // 12} năm {m % 12} tháng", help=f"{m} tháng")
            monthly_used, n_used = monthly4, m

    if n_used > 0:
        path, bal = [], float(init4)
        for m in range(n_used + 1):
            path.append({"Tháng": m, "Số dư": bal, "Mục tiêu": target})
            bal = (bal + monthly_used) * (1 + i4)
        st.line_chart(pd.DataFrame(path).set_index("Tháng"))

# ----------------------------------------------------------------------------
# TAB 5: RÚT TRƯỚC HẠN
# ----------------------------------------------------------------------------
with tab5:
    st.subheader("Rút tiền trước hạn thiệt bao nhiêu?")
    e1, e2 = st.columns(2)
    with e1:
        p5 = st.number_input("Số tiền gửi (VNĐ):", min_value=0, value=100_000_000, step=1_000_000,
                             format="%d", key="t5_p")
        r5 = st.number_input("Lãi suất kỳ hạn (%/năm):", min_value=0.0, value=6.0, step=0.1,
                             format="%.2f", key="t5_r")
    with e2:
        t5 = st.number_input("Kỳ hạn (tháng):", min_value=1, max_value=600, value=12, step=1, key="t5_t")
        nt5 = st.number_input("Lãi suất không kỳ hạn (%/năm):", min_value=0.0, value=0.1, step=0.05,
                              format="%.2f", key="t5_nt",
                              help="Rút trước hạn thường hưởng lãi không kỳ hạn (khoảng 0,1–0,5%/năm tùy ngân hàng).")

    total_days = round(t5 * 365 / 12)
    days_held = st.slider("Số ngày đã gửi khi rút:", 1, max(2, total_days - 1), min(90, max(1, total_days - 1)))

    full_interest = p5 * r5 / 100 * t5 / 12
    early_interest = p5 * nt5 / 100 * days_held / 365
    x1, x2, x3 = st.columns(3)
    x1.metric("Lãi nếu giữ đủ kỳ hạn", fmt_vnd(full_interest))
    x2.metric("Lãi nếu rút ở ngày này", fmt_vnd(early_interest))
    x3.metric("Số lãi bị mất", fmt_vnd(full_interest - early_interest), delta_color="inverse",
              delta=f"-{(1 - early_interest / full_interest) * 100:.1f}%" if full_interest > 0 else None)

    chart5 = pd.DataFrame({
        "Ngày rút": list(range(1, total_days)),
    })
    chart5["Lãi nhận nếu rút sớm"] = p5 * nt5 / 100 * chart5["Ngày rút"] / 365
    chart5["Lãi nếu giữ đủ kỳ hạn"] = full_interest
    st.line_chart(chart5.set_index("Ngày rút"))
    st.caption("💡 Nếu cần tiền gấp, hãy cân nhắc vay thế chấp sổ tiết kiệm hoặc chia nhỏ sổ (gửi nhiều sổ) để chỉ tất toán một phần.")

# ----------------------------------------------------------------------------
# TAB 6: LỊCH SỬ
# ----------------------------------------------------------------------------
with tab6:
    st.subheader("Lịch sử các phép tính đã lưu")
    history = st.session_state.get("history", [])
    if history:
        hdf = pd.DataFrame(history)
        st.dataframe(hdf, width="stretch", hide_index=True)
        h1, h2 = st.columns(2)
        h1.download_button("⬇️ Tải lịch sử (CSV)", to_csv(hdf), "lich_su_tinh_lai.csv", "text/csv")
        if h2.button("🗑️ Xóa lịch sử"):
            st.session_state["history"] = []
            st.rerun()
    else:
        st.info("Chưa có phép tính nào. Hãy bấm **💾 Lưu vào lịch sử** ở tab *Tính lãi*.")
