import os
import csv
import pandas as pd
import streamlit as st
from fpdf import FPDF

# 웹페이지 기본 설정
st.set_page_config(
    page_title="루트에어 AHU Selection Program", 
    page_icon="⚙️",
    layout="wide"
)

# 스타일 커스텀 (CSS)
st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; }
    .title-container {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 5px;
    }
    .title-container img {
        height: 45px;
        object-fit: contain;
    }
    .title-container h1 {
        margin: 0;
        color: #1E293B;
        font-family: 'Malgun Gothic', sans-serif;
        font-size: 2.2rem;
    }
    .stButton>button { width: 100%; font-weight: bold; background-color: #38BDF8 !important; color: #0F172A !important; border: none !important; }
    .stButton>button:hover { background-color: #0EA5E9 !important; }
    /* PDF 다운로드 버튼 스타일 (시인성 좋은 녹색 배치) */
    .stDownloadButton>button { width: 100%; font-weight: bold; background-color: #10B981 !important; color: #FFFFFF !important; border: none !important; }
    .stDownloadButton>button:hover { background-color: #059669 !important; }
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
            
    for enc in ['utf-8', 'cp949', 'utf-8-sig']:
        try:
            df = pd.read_csv(db_filename, encoding=enc)
            df.columns = df.columns.str.strip()
            if 'Range_CMH_Min' in df.columns:
                return df
        except Exception:
            continue
    return None

df = load_data()

# 🌟 [PDF 생성 함수 구조 개선]: 서버와 로컬 환경 모두에서 안전하게 한글 폰트 로딩
def generate_pdf(model_name, specs_list, input_conditions):
    pdf = FPDF()
    pdf.add_page()
    
    # [수정]: 윈도우 고정 경로 대신, 현재 프로그램이 실행 중인 폴더 안의 malgun.ttf 파일을 우선 탐색합니다.
    font_name = "malgun.ttf"
    font_path = os.path.join(os.getcwd(), font_name)
    
    # 만약 폴더 안에 없고 내 컴퓨터(윈도우)에서 돌릴 때를 대비한 백업 경로 추가
    if not os.path.exists(font_path):
        font_path = "C:\\Windows\\Fonts\\malgun.ttf"
        
    try:
        # 파일이 존재하는지 확실히 체크 후 폰트 등록
        if os.path.exists(font_path):
            pdf.add_font("Malgun", "", font_path)
            pdf.set_font("Malgun", size=11)
        else:
            # 폰트 파일이 아예 안 올라왔을 때 최후의 보루 (영어 기본 폰트로 튕김 에러 방지)
            pdf.set_font("helvetica", size=11)
    except:
        pdf.set_font("helvetica", size=11)

    # 1. 문서 헤더
    try:
        pdf.set_font("Malgun", style="B", size=20)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(190, 15, txt="루트에어 AHU 장비 선정 성적서", ln=True, align="C")
        
        pdf.set_font("Malgun", size=9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(190, 5, txt="ROOT AIR CO., LTD. | Technical Selection Report", ln=True, align="C")
    except:
        # 한글 깨짐 방지 폰트가 안 맞을 경우 영어 헤더 출력
        pdf.set_font("helvetica", style="B", size=20)
        pdf.cell(190, 15, txt="ROOT AIR - AHU Technical Report", ln=True, align="C")
    pdf.ln(10)
    
    # 2. 설계 조건 요약
    try:
        pdf.set_font("Malgun", style="B", size=12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(190, 8, txt="[1] 설계 입력 조건 (Design Input)", ln=True, align="L")
        pdf.set_font("Malgun", size=10)
        
        pdf.cell(45, 8, txt=" Required Air Flow:", border=1)
        pdf.cell(50, 8, txt=f" {input_conditions['cmh']:,} CMH", border=1)
        pdf.cell(45, 8, txt=" Cooling Load:", border=1)
        pdf.cell(50, 8, txt=f" {input_conditions['cool']:,} kcal/h", border=1, ln=True)
        
        pdf.cell(45, 8, txt=" Heating Load:", border=1)
        pdf.cell(50, 8, txt=f" {input_conditions['heat']:,} kcal/h", border=1)
        pdf.cell(45, 8, txt=" Heating Source:", border=1)
        pdf.cell(50, 8, txt=f" {input_conditions['heat_type']}", border=1, ln=True)
    except:
        pass
    pdf.ln(10)
    
    # 3. 선정 결과 상세 사양표
    try:
        pdf.set_font("Malgun", style="B", size=12)
        pdf.cell(190, 8, txt=f"[2] 추천 모델 사양 명세: {model_name}", ln=True, align="L")
        
        pdf.set_font("Malgun", style="B", size=10)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(70, 8, txt=" 사양 항목 (Specification)", border=1, fill=True)
        pdf.cell(120, 8, txt=" 기술 상세 데이터 (Technical Data)", border=1, fill=True, ln=True)
        
        pdf.set_font("Malgun", size=10)
        for spec, val in specs_list:
            pdf.cell(70, 8, txt=f" {spec}", border=1)
            pdf.cell(120, 8, txt=f" {val}", border=1, ln=True)
    except:
        pass
        
    pdf.ln(15)
    try:
        pdf.set_font("Malgun", size=9)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(190, 5, txt="* 본 성적서는 데이터베이스 기준 알고리즘에 의해 자동 생성된 기술 문서입니다.", ln=True, align="C")
    except:
        pass
    
    return pdf.output()

if df is None:
    st.error("❌ 데이터베이스(CSV) 파일을 찾을 수 없거나 열 사양이 올바르지 않습니다.")
else:
    # 타이틀 왼쪽에 회사 로고 배치
    if os.path.exists("company_logo.png"):
        import base64
        with open("company_logo.png", "rb") as image_file:
            encoded_logo = base64.b64encode(image_file.read()).decode()
        
        st.markdown(f"""
            <div class="title-container">
                <img src="data:image/png;base64,{encoded_logo}" alt="Company Logo">
                <h1>루트에어 AHU Selection Program</h1>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.title("루트에어 AHU Selection Program")
        
    st.caption(f"📊 Connected Database: {os.path.basename('AHU_Selection_Master_DB.csv')}")
    st.write("---")

    # 화면 분할
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
        
        # [AHRI 마크 배치]
        st.write("---")
        if os.path.exists("ahri_logo.png"):
            st.image("ahri_logo.png", caption="AHRI Certified Performance", width=140)

    with col_result:
        st.subheader("2. 최적 모델 선정 결과 (Output)")
        st.write("")

        if submit_btn or st.session_state.get('pdf_ready', False):
            if submit_btn:
                st.session_state['pdf_ready'] = True
                st.session_state['cmh_val'] = cmh
                st.session_state['cool_val'] = cool_req
                st.session_state['heat_val'] = heat_req
                st.session_state['heat_type_val'] = heat_type
            
            curr_cmh = st.session_state['cmh_val']
            curr_cool = st.session_state['cool_val']
            curr_heat = st.session_state['heat_val']
            curr_type = st.session_state['heat_type_val']
            
            candidates = df[(df['Range_CMH_Min'] <= curr_cmh) & (curr_cmh <= df['Range_CMH_Max'])]
            if candidates.empty:
                candidates = df[df['Range_CMH_Max'] >= curr_cmh]
                
            selected_row = None
            status_msg = "✅ 설계 조건에 맞는 최적의 장비가 선정되었습니다."
            status_type = "success"

            for _, row in candidates.iterrows():
                if row['Cooling_kcal_h'] >= curr_cool and row[heat_col] >= curr_heat:
                    selected_row = row
                    break

            if selected_row is None:
                all_larger = df[df['Range_CMH_Max'] >= curr_cmh]
                for _, row in all_larger.iterrows():
                    if row['Cooling_kcal_h'] >= curr_cool and row[heat_col] >= curr_heat:
                        selected_row = row
                        status_msg = "⚠️ 알림: 풍량 대비 부하가 커서 용량을 만족하는 한 단계 상위 모델이 선정되었습니다."
                        status_type = "warning"
                        break

            if selected_row is not None:
                if status_type == "success":
                    st.success(status_msg)
                else:
                    st.warning(status_msg)

                col_m1, col_m2 = st.columns([1, 1])
                with col_m1:
                    st.metric(label="✨ 추천 모델명", value=selected_row['Model_Name'])
                
                specs_list = [
                    ("표준 정격 풍량", f"{int(selected_row['STD_CMH']):,} CMH ({int(selected_row['Std_CMM'])} CMM)"),
                    ("적정 풍량 범위", f"{int(selected_row['Range_CMH_Min']):,} ~ {int(selected_row['Range_CMH_Max']):,} CMH"),
                    ("정격 냉방능력", f"{int(selected_row['Cooling_kcal_h']):,} kcal/h"),
                    (f"정격 난방능력 ({heat_label})", f"{int(selected_row[heat_col]):,} kcal/h"),
                    ("공급팬 (SF) 사이즈", selected_row['SF_Fan_Size']),
                    ("공급팬 모터 동력", f"{selected_row['SF_Motor_kW']} kW (정압 {int(selected_row['SF_Static_mmAq'])} mmAg)"),
                    ("환기팬 (RF) 사이즈", selected_row['RF_Fan_Size']),
                    ("환기팬 모터 동력", f"{selected_row['RF_Motor_kW']} kW (정압 {int(selected_row['RF_Static_mmAq'])} mmAg)"),
                    ("코일 패스 및 수량", f"{int(selected_row['Coil_Pass'])} Pass / {int(selected_row['Coil_Qty'])} 개"),
                    ("코일 크기 (H x W)", f"{int(selected_row['Coil_H'])} mm x {int(selected_row['Coil_W'])} mm"),
                    ("정면 면적 (Face Area)", f"{selected_row['Face_Area_m2']} m²"),
                    ("필터 배열", f"{selected_row['Filter_Row']} 단 x {selected_row['Filter_Col']} 열"),
                    ("표준 가습량", f"{int(selected_row['Humid_kg_h'])} Kg/h"),
                    ("냉온수 관경", f"{int(selected_row['Conn_Cool_In_Out_A'])} A x {int(selected_row['Conn_Cool_Qty'])} 개")
                ]

                input_conditions = {'cmh': curr_cmh, 'cool': curr_cool, 'heat': curr_heat, 'heat_type': curr_type}
                pdf_bytes = generate_pdf(selected_row['Model_Name'], specs_list, input_conditions)
                
                with col_m2:
                    st.write("") 
                    st.download_button(
                        label="📄 장비 선정 성적서 다운로드 (PDF)",
                        data=pdf_bytes,
                        file_name=f"루트에어_AHU_선정성적서_{selected_row['Model_Name']}.pdf",
                        mime="application/pdf"
                    )

                res_data = {
                    "사양 구분": [s[0] for s in specs_list],
                    "상세 데이터": [s[1] for s in specs_list]
                }
                res_df = pd.DataFrame(res_data)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
            else:
                st.error("❌ 에러: 요구하는 열부하 용량이 너무 커서 데이터베이스 내에 매칭 가능한 모델이 없습니다.")
        else:
            st.info("💡 좌측 입력창에 설계 조건을 입력한 후 [최적 장비 선정하기] 버튼을 누르세요.")