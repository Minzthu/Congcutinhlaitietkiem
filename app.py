import streamlit as st
st.image("logo.jpg")
# Cấu hình trang
st.set_page_config(page_title="Công Cụ Tính Lãi Tiết Kiệm", page_icon="💰", layout="centered")

def calculate_interest():
    st.title("Nơi lưu trữ giá trị cuộc sống✅")
    st.markdown("Công cụ giúp bạn ước tính số tiền lãi nhận được theo lãi đơn hoặc lãi kép.")

    # Tạo form nhập liệu
    with st.form("savings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            principal = st.number_input("Số tiền gửi (VNĐ):", min_value=0, value=100000000, step=1000000, format="%d")
            interest_rate = st.number_input("Lãi suất (%/năm):", min_value=0.0, value=6.0, step=0.1, format="%.2f")
            
        with col2:
            term_months = st.number_input("Kỳ hạn gửi (Tháng):", min_value=1, value=12, step=1)
            
            # Chọn loại lãi và hình thức
            interest_type = st.selectbox("Phương pháp tính lãi:", ["Lãi đơn", "Lãi kép"])
            payout_method = st.selectbox("Hình thức lãnh lãi / Kỳ ghép lãi:", ["Hàng tháng", "Hàng quý", "Cuối kỳ"])
            
        submitted = st.form_submit_button("Tính Toán 🧮")

    # Xử lý logic tính toán khi người dùng bấm nút
    if submitted:
        r = interest_rate / 100  # Chuyển đổi phần trăm sang số thập phân
        
        periodic_interest = 0
        total_interest = 0
        total_amount = principal
        
        # Cảnh báo nếu chọn hàng quý nhưng số tháng không chia hết cho 3
        if payout_method == "Hàng quý" and term_months % 3 != 0:
            st.warning("⚠️ Lưu ý: Kỳ hạn của bạn không chia hết cho 3 tháng. Phần dư sẽ được tính theo lãi suất không kỳ hạn (ở đây ứng dụng sẽ tính theo tỷ lệ thời gian).")
        
        # --- TÍNH THEO LÃI ĐƠN ---
        if interest_type == "Lãi đơn":
            if payout_method == "Hàng tháng":
                periodic_interest = principal * (r / 12)
                total_interest = periodic_interest * term_months
            elif payout_method == "Hàng quý":
                periodic_interest = principal * (r / 4)
                total_interest = periodic_interest * (term_months / 3)
            elif payout_method == "Cuối kỳ":
                periodic_interest = 0 # Không có lãi định kỳ
                total_interest = principal * r * (term_months / 12)
                
            total_amount = principal + total_interest

        # --- TÍNH THEO LÃI KÉP ---
        elif interest_type == "Lãi kép":
            # Đối với lãi kép, "Hình thức" đại diện cho tần suất ghép lãi (nhập gốc)
            if payout_method == "Hàng tháng":
                total_amount = principal * ((1 + r/12) ** term_months)
                total_interest = total_amount - principal
                # Lãi định kỳ thay đổi mỗi tháng nên để trống hoặc hiện "Lãi nhập gốc"
                periodic_interest = None 
                
            elif payout_method == "Hàng quý":
                periods = term_months / 3
                total_amount = principal * ((1 + r/4) ** periods)
                total_interest = total_amount - principal
                periodic_interest = None
                
            elif payout_method == "Cuối kỳ":
                # Kép cuối kỳ thường là ghép lãi theo năm
                years = term_months / 12
                total_amount = principal * ((1 + r) ** years)
                total_interest = total_amount - principal
                periodic_interest = None

        # Hiển thị kết quả bằng giao diện Metric trực quan
        st.markdown("### 📊 Kết Quả Tính Toán")
        st.markdown("---")
        
        col_res1, col_res2, col_res3 = st.columns(3)
        
        # Định dạng tiền tệ VNĐ
        def format_currency(val):
            return f"{val:,.0f} VNĐ"
        
        with col_res1:
            if interest_type == "Lãi đơn" and payout_method != "Cuối kỳ":
                st.metric(label=f"Tiền lãi nhận {payout_method.lower()}", value=format_currency(periodic_interest))
            elif interest_type == "Lãi kép" and payout_method != "Cuối kỳ":
                st.metric(label="Tiền lãi định kỳ", value="Nhập gốc 🔄")
            else:
                st.metric(label="Tiền lãi định kỳ", value="0 VNĐ (Nhận cuối kỳ)")
                
        with col_res2:
            st.metric(label="Tổng tiền lãi nhận được", value=format_currency(total_interest))
            
        with col_res3:
            st.metric(label="Tổng số tiền gốc & lãi", value=format_currency(total_amount))

if __name__ == "__main__":
    calculate_interest()
  
