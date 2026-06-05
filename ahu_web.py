import os
import csv
import pandas as pd
import streamlit as st
from fpdf import FPDF
from datetime import datetime
import base64

# 웹페이지 기본 설정
st.set_page_config(
    page_title="루트에어 AHU Selection Program", 
    page_icon="⚙️",
    layout="wide"
)

# 스타일 커스텀 (CSS)
st.markdown("""
    <style>
    .main .block-container { padding-top: 1.5rem; }
    .main-header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #FFFFFF;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 5px;
    }
    .header-left-logo, .header-right-logo {
        height: 50px;
        object-fit: contain;
    }
    .main-header-container h1 {
        margin: 0;
        color: #1E293B;
        font-family: 'Malgun Gothic', sans-serif;
        font-size: 2.3rem;
        font-weight: bold;
        text-align: center;
        flex-grow: 1;
    }
    .stButton>button { width: 100%; font-weight: bold; background-color: #38BDF8 !important; color: #0F172A !important; border: none !important; }
    .stButton>button:hover { background-color: #0EA5E9 !important; }
    .stDownloadButton>button { width: 100%; font-weight: bold; background-color: #10B981 !important; color: #FFFFFF !important; border: none !important; }
    .stDownloadButton>button:hover { background-color: #059669 !important; }
    </style>
    """, unsafe_allow_html=True)

# 데이터베이스 로드 함수
@st.cache_data
def load_data(filepath, file_mtime):
    if not os.path.exists(filepath):
        return None
            
    for enc in ['utf-8', 'cp949', 'utf-8-sig']:
        try:
            df = pd.read_csv(filepath, encoding=enc)
            df.columns = df.columns.str.strip()
            if 'Range_CMH_Min' in df.columns:
                return df
        except Exception:
            continue
    return None

db_filename = 'AHU_Selection_Master_DB.csv'
if not os.path.exists(db_filename):
    current_dir = os.getcwd()
    files = [f for f in os.listdir(current_dir) if f.lower().endswith('.csv')]
    if files:
        db_filename = files[0]

if os.path.exists(db_filename):
    df = load_data(db_filename, os.path.getmtime(db_filename))
else:
    df = None

if df is None:
    st.error("❌ 데이터베이스(CSV) 파일을 찾을 수 없습니다. 'AHU_Selection_Master_DB.csv' 파일이 저장소에 있는지 확인해 주세요.")
elif 'Type_H_HI' not in df.columns:
    st.error("❌ [알림] 인터넷 서버가 아직 구버전 CSV 파일의 기억을 붙잡고 있습니다. [Clear cache]를 진행해 주세요.")
else:
    # 상단 메인 헤더 바 랜더링
    left_logo_html = ""
    right_logo_html = ""
    if os.path.exists("company_logo.png"):
        with open("company_logo.png", "rb") as f:
            left_logo_bytes = base64.b64encode(f.read()).decode()
            left_logo_html = f'<img class="header-left-logo" src="data:image/png;base64,{left_logo_bytes}" alt="Company Logo">'
    if os.path.exists("ahri_logo.png"):
        with open("ahri_logo.png", "rb") as f:
            right_logo_bytes = base64.b64encode(f.read()).decode()
            right_logo_html = f'<img class="header-right-logo" src="data:image/png;base64,{right_logo_bytes}" alt="AHRI Logo">'
            
    st.markdown(f"""
        <div class="main-header-container">
            {left_logo_html}
            <h1>루트에어 AHU Selection Program</h1>
            {right_logo_html}
        </div>
        """, unsafe_allow_html=True)
        
    st.caption(f"📊 Connected Database: {os.path.basename(db_filename)}")
    st.write("---")

    # PDF 푸터 설정 클래스
    class RootAirPDF(FPDF):
        def footer(self):
            self.set_y(-15)
            try:
                self.set_font("Malgun", style="", size=8)
            except:
                self.set_font("helvetica", style="", size=8)
            self.set_text_color(148, 163, 184)
            footer_text = "Copyright © RootAir ALL RIGHTS RESERVED. | Tel: +82-02-2082-7654 | Email: rootair@rootair.co.kr"
            self.cell(190, 10, txt=footer_text, border=0, ln=False, align="C")

    # PDF 생성 함수
    def generate_pdf(model_name, specs_list, input_conditions, project_info):
        pdf = RootAirPDF()
        pdf.add_page()
        
        font_name = "malgun.ttf"
        font_path = os.path.join(os.getcwd(), font_name)
        if not os.path.exists(font_path):
            font_path = "C:\\Windows\\Fonts\\malgun.ttf"
            
        has_korean = False
        try:
            if os.path.exists(font_path):
                pdf.add_font("Malgun", "", font_path)
                pdf.add_font("Malgun", "B", font_path)
                pdf.set_font("Malgun", size=11)
                has_korean = True
            else:
                pdf.set_font("helvetica", size=11)
        except:
            pdf.set_font("helvetica", size=11)

        if os.path.exists("company_logo.png"):
            pdf.image("company_logo.png", x=10, y=10, w=30)
        if os.path.exists("ahri_logo.png"):
            pdf.image("ahri_logo.png", x=170, y=10, w=30)
            
        pdf.set_y(22)

        if has_korean:
            pdf.set_font("Malgun", style="", size=22)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(190, 12, txt="루트에어 AHU 장비 선정 성적서", ln=True, align="C")
            
            pdf.set_font("Malgun", style="", size=9)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(190, 5, txt="RootAir Inc. | Technical Selection Report", ln=True, align="C")
        else:
            pdf.set_font("helvetica", style="B", size=20)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(190, 12, txt="RootAir Inc. - AHU Technical Report", ln=True, align="C")
        pdf.ln(10)
        
        # 🌟 [버그 수정 완료]: 그레이 톤 채우기를 안전하게 제거하고 깔끔한 선(Border) 위주로 테이블 구조 수정
        if has_korean:
            pdf.set_font("Malgun", style="", size=10.5)
            pdf.set_text_color(51, 65, 85) # 진한 회색 본문 글씨
            
            # 첫 번째 행: 프로젝트명 & 작성자
            pdf.cell(30, 8, txt=" 프로젝트명", border=1, fill=False)
            pdf.cell(75, 8, txt=f" {project_info['project_name']}", border=1, fill=False)
            pdf.cell(25, 8, txt=" 작성자", border=1, fill=False)
            pdf.cell(60, 8, txt=f" {project_info['author']}", border=1, ln=True, fill=False)
            
            # 두 번째 행: 선정 일자
            pdf.cell(30, 8, txt=" 선정 일자", border=1, fill=False)
            pdf.cell(160, 8, txt=f" {project_info['date']}", border=1, ln=True, fill=False)
        pdf.ln(8)
        
        if has_korean:
            pdf.set_font("Malgun", style="", size=13)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(190, 8, txt="[1] 설계 입력 조건 (Design Input)", ln=True, align="L")
            pdf.set_font("Malgun", style="", size=10)
        else:
            pdf.set_font("helvetica", style="B", size=12)
            pdf.cell(190, 8, txt="[1] Design Input Conditions", ln=True, align="L")
            pdf.set_font("helvetica", size=10)
            
        pdf.cell(45, 8, txt=" Required Air Flow:", border=1)
        pdf.cell(50, 8, txt=f" {input_conditions['cmh']:,} CMH", border=1)
        pdf.cell(45, 8, txt=" Cooling Load:", border=1)
        pdf.cell(50, 8, txt=f" {input_conditions['cool']:,} kcal/h", border=1, ln=True)
        
        pdf.cell(45, 8, txt=" Heating Load:", border=1)
        pdf.cell(50, 8, txt=f" {input_conditions['heat']:,} kcal/h", border=1)
        pdf.cell(45, 8, txt=" Unit Layout Type:", border=1)
        pdf.cell(50, 8, txt=f" {input_conditions['ahu_type_label']}", border=1, ln=True)
        pdf.ln(10)
        
        if has_korean:
            pdf.set_font("Malgun", style="", size=13)
            pdf.cell(190, 8, txt=f"[2] 추천 모델 상세 기술 규격 명세: {model_name}", ln=True, align="L")
            pdf.set_font("Malgun", style="", size=10)
        else:
            pdf.set_font("helvetica", style="B", size=12)
            pdf.cell(190, 8, txt=f"[2] Technical Specification: {model_name}", ln=True, align="L")
            pdf.set_font("helvetica", style="B", size=10)
            
        # 하단 대형 기술규격 명세표 헤더 부분도 명시적으로 fill=True에 대응하는 색깔 처리 완료
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(75, 7, txt=" Specification Item", border=1, fill=True)
        pdf.cell(115, 7, txt=" Technical Data", border=1, fill=True, ln=True)
        
        if has_korean:
            pdf.set_font("Malgun", style="", size=9.5)
        else:
            pdf.set_font("helvetica", size=9.5)
            
        for spec, val in specs_list:
            pdf.cell(75, 7, txt=f" {spec}", border=1, fill=False)
            pdf.cell(115, 7, txt=f" {val}", border=1, ln=True, fill=False)
            
        pdf.ln(10)
        if has_korean:
            pdf.set_font("Malgun", style="", size=9)
            pdf.set_text_color(148, 163, 184)
            pdf.cell(190, 5, txt="* 본 성적서는 데이터베이스 규격에 따라 시스템 알고리즘에 의해 자동 생성된 공식 기술 문서입니다.", ln=True, align="C")
        
        pdf_output = pdf.output()
        if isinstance(pdf_output, str):
            return pdf_output.encode('latin1')
        return bytes(pdf_output)

    # 화면 레이아웃
    col_input, col_result = st.columns([1, 2], gap="large")

    with col_input:
        st.subheader("1. 프로젝트 정보 입력")
        proj_date = st.date_input("선정 일자", datetime.now())
        proj_name = st.text_input("프로젝트 명", placeholder="예: OO빌딩 신축공사")
        proj_author = st.text_input("작성자", placeholder="예: 홍길동 팀장")
        
        st.write("---")
        st.subheader("2. 설계 조건 입력 (Input)")
        
        ahu_type = st.radio("공조기 레이아웃 구조 선택", ["H형 (단일팬 컴팩트형)", "HI형 (환기팬 내장 풀스펙형)"])
        curr_selected_type = "H" if "H형" in ahu_type else "HI"
        
        cmh = st.number_input("필요 풍량 (CMH)", value=4500, step=100)
        cool_req = st.number_input("요구 냉방부하 (kcal/h)", value=35000, step=1000)
        heat_req = st.number_input("요구 난방부하 (kcal/h)", value=25000, step=1000)
        heat_type = st.radio("난방 코일 열원 종류", ["온수 (Water)", "증기 (Steam)"])

        heat_col = 'Heating_Water_kcal_h' if "온수" in heat_type else 'Heating_Steam_kcal_h'
        heat_label = "온수" if "온수" in heat_type else "증기"

        st.write("")
        submit_btn = st.button("🔍 최적 장비 선정하기")

    with col_result:
        st.subheader("3. 최적 모델 선정 결과 (Output)")
        st.write("")

        if submit_btn or st.session_state.get('pdf_ready', False):
            if submit_btn:
                st.session_state['pdf_ready'] = True
                st.session_state['cmh_val'] = cmh
                st.session_state['cool_val'] = cool_req
                st.session_state['heat_val'] = heat_req
                st.session_state['heat_type_val'] = heat_type
                st.session_state['ahu_type_val'] = ahu_type
                st.session_state['p_date'] = proj_date.strftime("%Y년 %m월 %d일")
                st.session_state['p_name'] = proj_name if proj_name else "미지정 프로젝트"
                st.session_state['p_author'] = proj_author if proj_author else "담당자"
            
            curr_cmh = st.session_state['cmh_val']
            curr_cool = st.session_state['cool_val']
            curr_heat = st.session_state['heat_val']
            curr_type = st.session_state['heat_type_val']
            curr_ahu_type = st.session_state['ahu_type_val']
            curr_selected_type = "H" if "H형" in curr_ahu_type else "HI"
            
            c_date = st.session_state['p_date']
            c_name = st.session_state['p_name']
            c_author = st.session_state['p_author']
            
            type_filtered_df = df[df['Type_H_HI'] == curr_selected_type]
            
            candidates = type_filtered_df[(type_filtered_df['Range_CMH_Min'] <= curr_cmh) & (curr_cmh <= type_filtered_df['Range_CMH_Max'])]
            if candidates.empty:
                candidates = type_filtered_df[type_filtered_df['Range_CMH_Max'] >= curr_cmh]
                
            selected_row = None
            status_msg = "✅ 설계 조건 및 장비 구조 형태에 부합하는 최적의 모델이 선정되었습니다."
            status_type = "success"

            for _, row in candidates.iterrows():
                if row['Cooling_kcal_h'] >= curr_cool and row[heat_col] >= curr_heat:
                    selected_row = row
                    break

            if selected_row is None:
                all_larger = type_filtered_df[type_filtered_df['Range_CMH_Max'] >= curr_cmh]
                for _, row in all_larger.iterrows():
                    if row['Cooling_kcal_h'] >= curr_cool and row[heat_col] >= curr_heat:
                        selected_row = row
                        status_msg = "⚠️ 알림: 풍량 대비 요구 부하가 커서 용량을 충족하는 한 단계 상위 모델이 안전 선정되었습니다."
                        status_type = "warning"
                        break

            if selected_row is not None:
                if status_type == "success":
                    st.success(status_msg)
                else:
                    st.warning(status_msg)

                st.info(f"📋 **Project:** {c_name} | 👤 **Author:** {c_author} | 📅 **Date:** {c_date}")

                col_m1, col_m2 = st.columns([1, 1])
                with col_m1:
                    st.metric(label="✨ 추천 모델명", value=selected_row['Model_Name'])
                
                specs_list = [
                    ("표준 정격 풍량", f"{int(selected_row['STD_CMH']):,} CMH ({int(selected_row['Std_CMM'])} CMM)"),
                    ("적정 풍량 범위", f"{int(selected_row['Range_CMH_Min']):,} ~ {int(selected_row['Range_CMH_Max']):,} CMH"),
                    ("정격 냉방능력", f"{int(selected_row['Cooling_kcal_h']):,} kcal/h"),
                    (f"정격 난방능력 ({heat_label})", f"{int(selected_row[heat_col]):,} kcal/h"),
                    ("장비 외형 규격 크기 (W × H × L)", f"{int(selected_row['Size_W']):,} × {int(selected_row['Size_H']):,} × {int(selected_row['Size_L']):,} mm"),
                    ("급기 접속관 (SA) 사이즈", f"{selected_row['Conn_SA']} mm"),
                    ("외기 접속관 (OA) 사이즈", f"{selected_row['Conn_OA']} mm"),
                    ("배기 접속관 (EA) 사이즈", f"{selected_row['Conn_EA']} mm" if selected_row['Type_H_HI'] == 'HI' else "- (컴팩트형 제외)"),
                    ("환기 접속관 (RA) 사이즈", f"{selected_row['Conn_RA']} mm"),
                    ("공급팬 (SF) 규격 사이즈", selected_row['SF_Fan_Size']),
                    ("공급팬 모터 동력", f"{selected_row['SF_Motor_kW']} kW (정압 {int(selected_row['SF_Static_mmAq'])} mmAg)"),
                    ("환기팬 (RF) 규격 사이즈", selected_row['RF_Fan_Size'] if selected_row['Type_H_HI'] == 'HI' else "- (컴팩트형 제외)"),
                    ("환기팬 모터 동력", f"{selected_row['RF_Motor_kW']} kW (정압 {int(selected_row['RF_Static_mmAq'])} mmAg)" if selected_row['Type_H_HI'] == 'HI' else "- (컴팩트형 제외)"),
                    ("코일 패스 및 수량", f"{int(selected_row['Coil_Pass'])} Pass / {int(selected_row['Coil_Qty'])} 개"),
                    ("코일 규격 크기 (H × W)", f"{int(selected_row['Coil_H'])} mm × {int(selected_row['Coil_W'])} mm"),
                    ("정면 면적 (Face Area)", f"{selected_row['Face_Area_m2']} m²"),
                    ("필터 배열 구조", f"{selected_row['Filter_Row']} 단 × {selected_row['Filter_Col']} 열"),
                    ("표준 정격 가습량", f"{int(selected_row['Humid_kg_h'])} Kg/h"),
                    ("냉온수 배관 관경", f"{int(selected_row['Conn_Cool_In_Out_A'])} A × {int(selected_row['Conn_Cool_Qty'])} 개")
                ]

                input_conditions = {
                    'cmh': curr_cmh, 
                    'cool': curr_cool, 
                    'heat': curr_heat, 
                    'heat_type': curr_type,
                    'ahu_type_label': curr_ahu_type
                }
                project_info = {'date': c_date, 'project_name': c_name, 'author': c_author}
                pdf_bytes = generate_pdf(selected_row['Model_Name'], specs_list, input_conditions, project_info)
                
                with col_m2:
                    st.write("") 
                    st.download_button(
                        label="📄 장비 선정 성적서 다운로드 (PDF)",
                        data=pdf_bytes,
                        file_name=f"루트에어_AHU_선정성적서_{c_name}_{selected_row['Model_Name']}.pdf",
                        mime="application/pdf"
                    )

                res_data = {
                    "사양 구분 항목": [s[0] for s in specs_list],
                    "상세 기술 데이터": [s[1] for s in specs_list]
                }
                res_df = pd.DataFrame(res_data)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
            else:
                st.error("❌ 에러: 요구하는 설계 사양이 너무 커서 데이터베이스 내에 매칭 가능한 루트에어 모델이 없습니다.")
        else:
            st.info("💡 좌측 입력창에 정보를 입력한 후 [최적 장비 선정하기] 버튼을 누르세요.")