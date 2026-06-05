import os
import csv
import pandas as pd
import streamlit as st

# 웹페이지 기본 설정
st.set_page_config(
    page_title="루트코리아 AHU 자동 선정 프로그램", 
    page_icon="⚙️",
    layout="wide"
)

# 스타일 커스텀 (CSS) - 깔끔한 엔지니어링 블루 톤
st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; }
    h1 { color: #1E293B; font-family: 'Malgun Gothic', sans-serif; }
    .stButton>button { width: 100%; font-weight: bold; background-color: #38BDF8 !important; color: #0F172A !important; border: none !important; }
    .stButton>button:hover { background-color: #0EA5E9 !important; }
    </style>
    """, unsafe_allow_html=True)

# 데이터베이스 로드 함수
@st.cache_data
def load_data():
    db_filename = 'AHU_Selection_Master_DB.csv'
    if not os.path.exists(db_filename):
        current_dir = os.getcwd()
        files = [f for f in os.listdir(current_dir) if f.lower().endswith('.csv')]
        if files:
            db_filename = files[0]
        else:
            return None
    try:
        return pd.read_csv(db_filename, encoding='utf-8')
    except Exception:
        try:
            return pd.read_csv(db_filename, encoding='cp949')
        except Exception:
            return None

df = load_data()

if df is None:
    st.error("❌ 데이터베이스(CSV) 파일을 찾을 수 없습니다.")
else:
    # 메인 타이틀 영역
    st.title("⚙️ AHU 자동 선정 시스템 Web v1.2")
    st.caption(f"📊 연결된 데이터베이스: {os.path.basename('AHU_Selection_Master_DB.csv')}")
    st.write("---")

    # 화면 분할 (입력창 1 : 결과창 2)
    col_input, col_result = st.columns([1, 2], gap="large")

    with col_input:
        st.subheader("1. 설계 조건 입력 (Input)")
        
        cmh = st.number_input("필요 풍량 (CMH)", value=4500, step=100)
        cool_req = st.number_input("요구 냉방부하 (kcal/h)", value=35000, step=1000)
        heat_req = st.number_input("요구 난방부하 (kcal/h)", value=25000, step=1000)
        heat_type = st.radio("난방 코일 열원 종류", ["온수 (Water)", "증기 (Steam)"])

        heat_col = 'Heating_Water_kcal_h' if "온수" in heat_type else 'Heating_Steam_kcal_h'
        heat_label = "온수" if "온수" in heat_type else "증기"

        st.write("")
        submit_btn = st.button("🔍 최적 장비 선정하기")
        
        # 🌟 [AHRI 마크 배치] - 실제 깃허브 주소인 root-air-selection 으로 경로를 수정했습니다!
        st.write("---")
        ahri_logo_url = "https://raw.githubusercontent.com/hklim-byt/root-air-selection/main/ahri_logo.png"
        st.image(ahri_logo_url, caption="AHRI Certified Performance", width=140, output_format="PNG")

    with col_result:
        # 🌟 [결과창 타이틀 & 회사 로고 가로 배열]
        col_res_title, col_logo = st.columns([2, 1])
        with col_res_title:
            st.subheader("2. 최적 모델 선정 결과 (Output)")
        with col_logo:
            # 🌟 [회사 로고 배치] - 실제 깃허브 주소인 root-air-selection 으로 경로를 수정했습니다!
            company_logo_url = "https://raw.githubusercontent.com/hklim-byt/root-air-selection/main/company_logo.png"
            st.image(company_logo_url, width=180, output_format="PNG")
            
        st.write("")

        if submit_btn:
            candidates = df[(df['Range_CMH_Min'] <= cmh) & (cmh <= df['Range_CMH_Max'])]
            if candidates.empty:
                candidates = df[df['Range_CMH_Max'] >= cmh]
                
            selected_row = None
            status_msg = "✅ 설계 조건에 맞는 최적의 장비가 선정되었습니다."
            status_type = "success"

            for _, row in candidates.iterrows():
                if row['Cooling_kcal_h'] >= cool_req and row[heat_col] >= heat_req:
                    selected_row = row
                    break

            if not selected_row:
                all_larger = df[df['Range_CMH_Max'] >= cmh]
                for _, row in all_larger.iterrows():
                    if row['Cooling_kcal_h'] >= cool_req and row[heat_col] >= heat_req:
                        selected_row = row
                        status_msg = "⚠️ 알림: 풍량 대비 부하가 커서 용량을 만족하는 한 단계 상위 모델이 선정되었습니다."
                        status_type = "warning"
                        break

            if selected_row is not None:
                if status_type == "success":
                    st.success(status_msg)
                else:
                    st.warning(status_msg)

                st.metric(label="✨ 추천 모델명", value=selected_row['Model_Name'])
                
                res_data = {
                    "사양 구분": [
                        "표준 정격 풍량", "적정 풍량 범위", "정격 냉방능력", f"정격 난방능력 ({heat_label})",
                        "공급팬 (SF) 사이즈", "공급팬 모터 동력", "환기팬 (RF) 사이즈", "환기팬 모터 동력",
                        "코일 패스 및 수량", "코일 크기 (H x W)", "정면 면적 (Face Area)", "필터 배열",
                        "표준 가습량", "냉온수 관경"
                    ],
                    "상세 데이터": [
                        f"{int(selected_row['STD_CMH']):,} CMH ({int(selected_row['Std_CMM'])} CMM)",
                        f"{int(selected_row['Range_CMH_Min']):,} ~ {int(selected_row['Range_CMH_Max']):,} CMH",
                        f"{int(selected_row['Cooling_kcal_h']):,} kcal/h",
                        f"{int(selected_row[heat_col]):,} kcal/h",
                        selected_row['SF_Fan_Size'],
                        f"{selected_row['SF_Motor_kW']} kW (정압 {int(selected_row['SF_Static_mmAq'])} mmAg)",
                        selected_row['RF_Fan_Size'],
                        f"{selected_row['RF_Motor_kW']} kW (정압 {int(selected_row['RF_Static_mmAq'])} mmAg)",
                        f"{int(selected_row['Coil_Pass'])} Pass / {int(selected_row['Coil_Qty'])} 개",
                        f"{int(selected_row['Coil_H'])} mm x {int(selected_row['Coil_W'])} mm",
                        f"{selected_row['Face_Area_m2']} m²",
                        f"{selected_row['Filter_Row']} 단 x {selected_row['Filter_Col']} 열",
                        f"{int(selected_row['Humid_kg_h'])} Kg/h",
                        f"{int(selected_row['Conn_Cool_In_Out_A'])} A x {int(selected_row['Conn_Cool_Qty'])} 개"
                    ]
                }
                res_df = pd.DataFrame(res_data)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
            else:
                st.error("❌ 에러: 요구하는 열부하 용량이 너무 커서 데이터베이스 내에 매칭 가능한 모델이 없습니다.")
        else:
            st.info("💡 좌측 입력창에 설계 조건을 입력한 후 [최적 장비 선정하기] 버튼을 누르세요.")