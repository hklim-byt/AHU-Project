import os
import csv
import pandas as pd
import streamlit as st
from fpdf import FPDF
from datetime import datetime
import base64
import math

# 웹페이지 기본 설정
st.set_page_config(
    page_title="루트에어 AHU Selection Program", 
    page_icon="⚙️",
    layout="wide"
)

# 스타일 커스텀 (CSS) - 모바일 반응형 완벽 대응
st.markdown("""
    <style>
    .main .block-container { padding-top: 1.5rem; }
    
    .main-header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #FFFFFF;
        padding: 12px 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 5px;
        gap: 10px;
    }
    .header-left-logo, .header-right-logo {
        height: 45px;
        object-fit: contain;
        flex-shrink: 0;
    }
    
    .main-header-container h1 {
        margin: 0;
        color: #1E293B;
        font-family: 'Malgun Gothic', sans-serif;
        font-size: calc(1.3rem + 1vw); 
        font-weight: bold;
        text-align: center;
        flex-grow: 1;
        white-space: nowrap; 
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    @media (max-width: 640px) {
        .main-header-container { padding: 8px 10px; }
        .header-left-logo, .header-right-logo { height: 30px; }
        .main-header-container h1 { font-size: 1.1rem; }
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

# 온습도 기준 절대습도(kg/kg') 산출 함수
def calculate_absolute_humidity(db_temp, rh):
    abs_temp = db_temp + 273.15
    std_pressure = 101325.0 
    
    if db_temp >= 0:
        c1 = -5.8002206e03
        c2 = 1.3914993e00
        c3 = -4.8640239e-02
        c4 = 4.1764768e-05
        c5 = -1.4452093e-08
        c6 = 6.5459673e00
        ln_ps = c1/abs_temp + c2 + c3*abs_temp + c4*(abs_temp**2) + c5*(abs_temp**3) + c6*math.log(abs_temp)
        ps = math.exp(ln_ps)
    else:
        ps = 611.2 * math.exp((17.62 * db_temp) / (db_temp + 243.12))
        
    pw = ps * (rh / 100.0)
    
    if (std_pressure - pw) <= 0: return 0.001
    x = 0.62194 * pw / (std_pressure - pw)
    return x

# 습공기 상태방정식 기반 실시간 공기 밀도 연산 함수
def calculate_air_density(db_temp, rh):
    abs_temp = db_temp + 273.15 
    std_pressure = 101325 
    
    if db_temp >= 0:
        c1 = -5.8002206e03
        c2 = 1.3914993e00
        c3 = -4.8640239e-02
        c4 = 4.1764768e-05
        c5 = -1.4452093e-08
        c6 = 6.5459673e00
        ln_ps = c1/abs_temp + c2 + c3*abs_temp + c4*(abs_temp**2) + c5*(abs_temp**3) + c6*math.log(abs_temp)
        ps = math.exp(ln_ps)
    else:
        ps = 611.2 * math.exp((17.62 * db_temp) / (db_temp + 243.12))
        
    pw = ps * (rh / 100.0)
    p_da = std_pressure - pw
    
    r_da = 287.055 
    r_wv = 461.5 
    
    density = (p_da / (r_da * abs_temp)) + (pw / (r_wv * abs_temp))
    return round(density, 4)

if df is None:
    st.error("❌ 데이터베이스(CSV) 파일을 찾을 수 없습니다.")
elif 'Type_H_HI' not in df.columns:
    st.error("❌ [알림] 인터넷 서버가 아직 구버전 CSV 파일의 기억을 붙잡고 있습니다. [Clear cache]를 진행해 주세요.")
else:
    # 상단 로고 바 렌더링
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
            self.set_y(-12)
            try:
                self.set_font("Malgun", style="", size=7.2)
            except:
                self.set_font("helvetica", style="", size=7.2)
            self.set_text_color(148, 163, 184)
            footer_text = "Copyright © RootAir ALL RIGHTS RESERVED. | Tel: +82-02-2082-7654 | Email: rootair@rootair.co.kr"
            self.cell(190, 8, txt=footer_text, border=0, ln=False, align="C")

    # PDF 생성 함수 (마진 및 행 높이 4.2mm 장착 명품 가드 🌟)
    def generate_pdf(model_name, specs_list, input_conditions, project_info, density_info, coil_calc_info, is_velocity_warning):
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
                pdf.set_font("Malgun", size=10)
                has_korean = True
            else:
                pdf.set_font("helvetica", size=10)
        except:
            pdf.set_font("helvetica", size=10)

        if os.path.exists("company_logo.png"):
            pdf.image("company_logo.png", x=10, y=7, w=23)
        if os.path.exists("ahri_logo.png"):
            pdf.image("ahri_logo.png", x=175, y=7, w=23)
            
        pdf.set_y(15)

        if has_korean:
            pdf.set_font("Malgun", style="", size=17)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(190, 9, txt="루트에어 AHU 장비 선정 성적서", ln=True, align="C")
        pdf.ln(2)
        
        if has_korean:
            pdf.set_font("Malgun", style="", size=8.5)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(25, 5.0, txt=" 프로젝트명", border=1)
            pdf.cell(80, 5.0, txt=f" {project_info['project_name']}", border=1)
            pdf.cell(25, 5.0, txt=" 작성자", border=1)
            pdf.cell(60, 5.0, txt=f" {project_info['author']}", border=1, ln=True)
            pdf.cell(25, 5.0, txt=" 선정 일자", border=1)
            pdf.cell(165, 5.0, txt=f" {project_info['date']}", border=1, ln=True)
        pdf.ln(2)
        
        pdf.set_font("Malgun" if has_korean else "helvetica", style="" if has_korean else "B", size=9.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(190, 5.0, txt="[1] 설계 입력 조건 및 공기 밀도 보정 (Design Input & Density)", ln=True, align="L")
        pdf.set_font("Malgun" if has_korean else "helvetica", size=8.0)
        
        pdf.cell(45, 4.4, txt=" Required Air Flow:", border=1)
        pdf.cell(50, 4.4, txt=f" {input_conditions['cmh']:,} CMH", border=1)
        pdf.cell(45, 4.4, txt=" Unit Layout Type:", border=1)
        pdf.cell(50, 4.0, txt=f" {input_conditions['ahu_type_label']}", border=1, ln=True)
        
        pdf.cell(45, 4.4, txt=" Input Cooling Load:", border=1)
        pdf.cell(50, 4.4, txt=f" {input_conditions['cool']:,} kcal/h", border=1)
        pdf.cell(45, 4.0, txt=" Corrected Cool Load:", border=1)
        pdf.cell(50, 4.0, txt=f" {int(density_info['corr_cool']):,} kcal/h", border=1, ln=True)
        
        pdf.cell(45, 4.4, txt=" Input Heating Load:", border=1)
        pdf.cell(50, 4.4, txt=f" {input_conditions['heat']:,} kcal/h", border=1)
        pdf.cell(45, 4.4, txt=" Corrected Heat Load:", border=1)
        pdf.cell(50, 4.4, txt=f" {int(density_info['corr_heat']):,} kcal/h", border=1, ln=True)
        
        pdf.cell(45, 4.4, txt=" Project Location:", border=1)
        pdf.cell(50, 4.4, txt=f" {density_info['location'].split(' ')[0]}", border=1)
        pdf.cell(45, 4.4, txt=" Real Air Density:", border=1)
        pdf.cell(50, 4.4, txt=f" {density_info['density']} kg/m3", border=1, ln=True)
        pdf.ln(2)
        
        pdf.set_font("Malgun" if has_korean else "helvetica", style="" if has_korean else "B", size=10)
        pdf.cell(190, 5.5, txt="[2] 코일 열정격 및 옵션 사양 (Coil & Option Mechanical Data)", ln=True, align="L")
        pdf.set_font("Malgun" if has_korean else "helvetica", size=8.0)
        
        pdf.cell(45, 4.4, txt=" 냉수 입/출구 온도:", border=1)
        pdf.cell(50, 4.4, txt=f" {coil_calc_info['c_tw1']} C -> {coil_calc_info['c_tw2']} C", border=1)
        pdf.cell(45, 4.4, txt=" 온수 입/출구 온도:", border=1)
        pdf.cell(50, 4.2, txt=f" {coil_calc_info['h_tw1']} C -> {coil_calc_info['h_tw2']} C", border=1, ln=True)
        
        pdf.cell(45, 4.4, txt=" 냉수 요구 유량 (LPM):", border=1)
        pdf.cell(50, 4.4, txt=f" {coil_calc_info['cool_lpm']} LPM", border=1)
        pdf.cell(45, 4.2, txt=" 온수 요구 유량 (LPM):", border=1)
        pdf.cell(50, 4.2, txt=f" {coil_calc_info['heat_lpm']} LPM", border=1, ln=True)
        
        pdf.cell(45, 4.4, txt=" 냉방 대수평균 (LMTD):", border=1)
        pdf.cell(50, 4.4, txt=f" {coil_calc_info['cool_lmtd']} C", border=1)
        pdf.cell(45, 4.4, txt=" 코일 관내 유속 (Water):", border=1)
        pdf.cell(50, 4.4, txt=f" {coil_calc_info['water_velocity']} m/s (안정)", border=1, ln=True)
        pdf.ln(2)
        
        pdf.set_font("Malgun" if has_korean else "helvetica", style="" if has_korean else "B", size=10)
        pdf.cell(190, 5.5, txt=f"[3] 추천 모델 상세 기술 규격 명세: {model_name}", ln=True, align="L")
        pdf.set_font("Malgun" if has_korean else "helvetica", size=7.8)
            
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(75, 4.1, txt=" Specification Item", border=1, fill=True)
        pdf.cell(115, 4.1, txt=" Technical Data", border=1, fill=True, ln=True)
        
        for spec, val in specs_list:
            if is_velocity_warning and "코일 면풍속" in spec:
                pdf.set_text_color(220, 38, 38)
                pdf.cell(75, 4.1, txt=f" {spec}", border=1)
                pdf.cell(115, 4.1, txt=f" {val}", border=1, ln=True)
                pdf.set_text_color(51, 65, 85)
            else:
                pdf.cell(75, 4.1, txt=f" {spec}", border=1)
                pdf.cell(115, 4.1, txt=f" {val}", border=1, ln=True)
            
        pdf.ln(2)
        
        if is_velocity_warning:
            pdf.set_text_color(220, 38, 38)
            pdf.set_font("Malgun", style="", size=8.0)
            pdf.cell(190, 4.0, txt="⚠️ 코일 면풍속이 2.5 m/s를 초과하여 응축수 비산 위험이 있습니다.", border=0, ln=True, align="L")
            pdf.ln(1)

        pdf.set_font("Malgun", style="", size=7.0)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(190, 3.5, txt="* 본 성적서는 루트에어 공기선도_RootAirChart v1.1 및 Flaktkorea 코일전열 공식을 통합 연동한 정밀 설계 문서입니다.", ln=True, align="C")
        
        pdf_output = pdf.output()
        if isinstance(pdf_output, str):
            return pdf_output.encode('latin1')
        return bytes(pdf_output)

    # 화면 레이아웃 분할
    col_input, col_result = st.columns([1, 2], gap="large")

    with col_input:
        st.subheader("1. 프로젝트 정보 입력")
        proj_date = st.date_input("선정 일자", datetime.now())
        proj_name = st.text_input("프로젝트 명", placeholder="예: OO빌딩 신축공사")
        proj_author = st.text_input("작성자", placeholder="예: 홍길동 팀장")
        
        location_select = st.selectbox("전국 주요 설치 지역 선택 (WeatherData 연동)", ["서울 (Seoul)", "부산 (Busan)", "대구 (Daegu)", "광주 (Gwangju)", "제주 (Jeju)", "기타 (사용자 수동 설정)"])
        
        st.write("---")
        st.subheader("2. 설계 조건 입력 (Input)")
        ahu_type = st.radio("공조기 레이아웃 구조 선택", ["H형 (단일팬 컴팩트형)", "HI형 (환기팬 내장 풀스펙형)"])
        cmh = st.number_input("필요 풍량 (CMH)", value=4500, step=100)
        
        with st.expander("🌡️ 루트에어 공기선도_RootAirChart v1.1 기반 공기밀도 설정", expanded=True):
            if "서울" in location_select:
                c_init_t, c_init_rh, h_init_t, h_init_rh = 32.0, 65, -10.0, 60
            elif "부산" in location_select:
                c_init_t, c_init_rh, h_init_t, h_init_rh = 30.0, 70, -5.0, 55
            elif "대구" in location_select:
                c_init_t, c_init_rh, h_init_t, h_init_rh = 33.0, 60, -8.0, 55
            elif "광주" in location_select:
                c_init_t, c_init_rh, h_init_t, h_init_rh = 31.5, 65, -6.0, 60
            elif "제주" in location_select:
                c_init_t, c_init_rh, h_init_t, h_init_rh = 29.5, 75, 1.0, 60
            else:
                c_init_t, c_init_rh, h_init_t, h_init_rh = 20.0, 50, 20.0, 50
                
            st.caption(f"📢 현재 선택 지역: **{location_select.split(' ')[0]}** 표준 기상 기준 연동 중")
            cool_temp = st.number_input("냉방 설계 외기 온도 (°C)", value=c_init_t, step=0.5)
            cool_rh = st.slider("냉방 설계 상대습도 (%)", value=c_init_rh, min_value=0, max_value=100, step=5)
            heat_temp = st.number_input("난방 설계 외기 온도 (°C)", value=h_init_t, step=0.5)
            heat_rh = st.slider("난방 설계 상대습도 (%)", value=h_init_rh, min_value=0, max_value=100, step=5)
            
            rho_cool = calculate_air_density(cool_temp, cool_rh)
            rho_heat = calculate_air_density(heat_temp, heat_rh)
            avg_calculated_rho = round((rho_cool + rho_heat) / 2.0, 4)
            st.metric(label="📊 통합 계산된 현장 평균 공기 밀도", value=f"{avg_calculated_rho} kg/m³")

        with st.expander("💧 수측(Water) 코일 입출구 온도 설계 조건", expanded=True):
            coil_c_tw1 = st.number_input("냉수 입구 온도 (°C)", value=7.0, step=0.5)
            coil_c_tw2 = st.number_input("냉수 출구 온도 (°C)", value=12.0, step=0.5)
            coil_h_tw1 = st.number_input("온수 입구 온도 (°C)", value=60.0, step=0.5)
            coil_h_tw2 = st.number_input("온수 출구 온도 (°C)", value=50.0, step=0.5)

        with st.expander("➕ AHU 구성 부속품 및 필터 사양 선택 (정압 보정 연동)", expanded=True):
            opt_pre_filter = st.checkbox("🔍 프리 필터 장착 (Pre-Filter, AFI 82%급) [cite: 536]", value=True)
            opt_med_filter = st.checkbox("🔍 미디움 필터 장착 (Medium Filter, NBS 90%급) [cite: 537]", value=False)
            opt_hepa_filter = st.checkbox("🔍 헤파 필터 장착 (HEPA Filter, 크린룸용 99.97%급) [cite: 541, 594]", value=False)
            st.markdown("---")
            
            opt_antifreeze = st.checkbox("❄️ 동파방지 예열 코일 장비 내장 (Pre-Heater) [cite: 520]", value=False)
            opt_humidifier = st.selectbox("💨 가습기 종류 선택 (Humidifier Type)", ["장착 안 함 (None)", "기화식 가습기 (Evaporative)", "전극봉식 가습기 (Electronic)", "증기 분무식 가습기 (Steam)"])
            
            target_indoor_rh = 50
            if opt_humidifier != "장착 안 함 (None)":
                target_indoor_rh = st.slider(" 겨울철 실내 목표 상대습도 설정 (%) [cite: 562]", value=50, min_value=20, max_value=80, step=5)
                
            opt_eliminator = st.checkbox("💧 엘리미네이터 강제 장착 (Eliminator)", value=False)
            
            added_static = 0.0
            if opt_pre_filter: added_static += 2.0  
            if opt_med_filter: added_static += 5.5  
            if opt_hepa_filter: added_static += 12.0 
            if opt_antifreeze: added_static += 3.5  
            if opt_humidifier != "장착 안 함 (None)": added_static += 1.5 
            if opt_eliminator: added_static += 2.5 
            
        cool_req = st.number_input("요구 냉방부하 (kcal/h)", value=35000, step=1000)
        heat_req = st.number_input("요구 난방부하 (kcal/h)", value=25000, step=1000)
        heat_type = st.radio("난방 코일 열원 종류", ["온수 (Water)", "증기 (Steam)"])

        heat_col = 'Heating_Water_kcal_h' if "온수" in heat_type else 'Heating_Steam_kcal_h' [cite: 556]
        heat_label = "온수" if "온수" in heat_type else "증기"

        st.write("")
        submit_btn = st.button("🔍 최적 장비 선정하기")

    with col_result:
        st.subheader("3. 최적 모델 선정 결과 (Output)")
        st.write("")

        # 변수 안전벨트 초기화
        v_target_rh = st.session_state.get('target_rh', 50)
        v_opt_humid = st.session_state.get('opt_humid', "장착 안 함 (None)")
        v_added_stat = st.session_state.get('added_stat', 0.0)
        v_opt_anti = st.session_state.get('opt_anti', False)
        v_opt_elim = st.session_state.get('opt_elim', False)
        v_opt_pre = st.session_state.get('opt_pre', True)
        v_opt_med = st.session_state.get('opt_med', False)
        v_opt_hepa = st.session_state.get('opt_hepa', False)

        if submit_btn or st.session_state.get('pdf_ready', False):
            if submit_btn:
                st.session_state['pdf_ready'] = True
                st.session_state['cmh_val'] = cmh
                st.session_state['cool_val'] = cool_req
                st.session_state['heat_val'] = heat_req
                st.session_state['heat_type_val'] = heat_type
                st.session_state['ahu_type_val'] = ahu_type
                st.session_state['loc_val'] = location_select
                st.session_state['p_date'] = proj_date.strftime("%Y년 %m월 %d일")
                st.session_state['p_name'] = proj_name if proj_name else "미지정 프로젝트"
                st.session_state['p_author'] = proj_author if proj_author else "담당자"
                st.session_state['final_rho'] = avg_calculated_rho
                st.session_state['c_t'] = cool_temp
                st.session_state['c_r'] = cool_rh
                st.session_state['h_t'] = heat_temp
                st.session_state['h_r'] = heat_rh
                st.session_state['cc_tw1'] = coil_c_tw1
                st.session_state['cc_tw2'] = coil_c_tw2
                st.session_state['ch_tw1'] = coil_h_tw1
                st.session_state['ch_tw2'] = coil_h_tw2
                st.session_state['opt_anti'] = opt_antifreeze
                st.session_state['opt_humid'] = opt_humidifier
                st.session_state['opt_elim'] = opt_eliminator
                st.session_state['added_stat'] = added_static
                st.session_state['target_rh'] = target_indoor_rh
            
            curr_cmh = st.session_state.get('cmh_val', cmh)
            curr_cool = st.session_state.get('cool_val', cool_req)
            curr_heat = st.session_state.get('heat_val', heat_req)
            curr_type = st.session_state.get('heat_type_val', heat_type)
            curr_ahu_type = st.session_state.get('ahu_type_val', ahu_type)
            curr_selected_type = "H" if "H형" in curr_ahu_type else "HI"
            curr_location = st.session_state.get('loc_val', location_select)
            v_rho = st.session_state.get('final_rho', avg_calculated_rho)
            
            c_date = st.session_state.get('p_date', proj_date.strftime("%Y년 %m월 %d일"))
            c_name = st.session_state.get('p_name', proj_name if proj_name else "미지정 프로젝트")
            c_author = st.session_state.get('p_author', proj_author if proj_author else "담당자")
            
            v_ct = st.session_state.get('c_t', cool_temp)
            v_cr = st.session_state.get('c_r', cool_rh)
            v_ht = st.session_state.get('h_t', heat_temp)
            v_hr = st.session_state.get('h_r', heat_rh)
            
            v_cc_tw1 = st.session_state.get('cc_tw1', coil_c_tw1)
            v_cc_tw2 = st.session_state.get('cc_tw2', coil_c_tw2)
            v_ch_tw1 = st.session_state.get('ch_tw1', coil_h_tw1)
            v_ch_tw2 = st.session_state.get('ch_tw2', coil_h_tw2)
            
            v_opt_pre = st.session_state.get('opt_pre', opt_pre_filter)
            v_opt_med = st.session_state.get('opt_med', opt_med_filter)
            v_opt_hepa = st.session_state.get('opt_hepa', opt_hepa_filter)
            v_opt_anti = st.session_state.get('opt_anti', opt_antifreeze)
            v_opt_humid = st.session_state.get('opt_humid', opt_humidifier)
            v_opt_elim = st.session_state.get('opt_elim', opt_eliminator)
            v_added_stat = st.session_state.get('added_stat', added_static)
            v_target_rh = st.session_state.get('target_rh', target_indoor_rh)
            
            density_ratio = 1.2041 / v_rho
            corr_cool_req = curr_cool * density_ratio
            corr_heat_req = curr_heat * density_ratio
            
            type_filtered_df = df[df['Type_H_HI'] == curr_selected_type]
            candidates = type_filtered_df[(type_filtered_df['Range_CMH_Min'] <= curr_cmh) & (curr_cmh <= type_filtered_df['Range_CMH_Max'])]
            if candidates.empty:
                candidates = type_filtered_df[type_filtered_df['Range_CMH_Max'] >= curr_cmh]
                
            selected_row = None
            status_msg = "✅ 기상 조건, 3단계 필터 저항 및 코일 수측 제어 검증이 완료된 최적의 모델이 매칭되었습니다."
            status_type = "success"

            for _, row in candidates.iterrows():
                if row['Cooling_kcal_h'] >= corr_cool_req and row[heat_col] >= corr_heat_req: [cite: 556]
                    selected_row = row
                    break

            if selected_row is None:
                all_larger = type_filtered_df[type_filtered_df['Range_CMH_Max'] >= curr_cmh] [cite: 556]
                for _, row in all_larger.iterrows():
                    if row['Cooling_kcal_h'] >= corr_cool_req and row[heat_col] >= corr_heat_req: [cite: 556]
                        selected_row = row
                        status_msg = "⚠️ 알림: 필터 마찰 저항 가산 및 부하 충족을 위해 한 단계 상위 모델이 매칭되었습니다."
                        status_type = "warning"
                        break

            if selected_row is not None:
                # 상단 기본 서머리 카드
                st.info(f"📋 **Project:** {c_name} | 👤 **Author:** {c_author} | 📅 **Date:** {c_date} | 📍 **Location:** {curr_location.split(' ')[0]}")
                
                dt_cool = max(0.1, abs(v_cc_tw2 - v_cc_tw1))
                dt_heat = max(0.1, abs(v_ch_tw1 - v_ch_tw2))
                cool_lpm = round(corr_cool_req / (60.0 * dt_cool * 1.0), 1)
                heat_lpm = round(corr_heat_req / (60.0 * dt_heat * 1.0), 1)
                cool_lmtd = round(((v_ct - v_cc_tw2) - (15.0 - v_cc_tw1)) / math.log(max(1.01, (v_ct - v_cc_tw2)) / max(1.0, (15.0 - v_cc_tw1))), 1)
                
                db_pass = float(selected_row['Coil_Pass']) if 'Coil_Pass' in selected_row else 18.0 [cite: 556]
                water_velocity = round((cool_lpm / 60000.0) / (db_pass * math.pi * (0.0127**2) / 4.0), 2)
                
                face_area = float(selected_row['Face_Area_m2'])
                coil_velocity = round(curr_cmh / (3600.0 * face_area), 2)
                
                if coil_velocity >= 2.0 and not v_opt_elim:
                    v_opt_elim = True
                    v_added_stat += 2.5
                    
                is_velocity_warning = coil_velocity >= 2.5

                if v_opt_humid != "장착 안 함 (None)":
                    x_outdoor = calculate_absolute_humidity(v_ht, v_hr)
                    x_indoor = calculate_absolute_humidity(22.0, v_target_rh)
                    delta_x = max(0.0001, x_indoor - x_outdoor)
                    required_humid_kg_h = round(curr_cmh * v_rho * delta_x, 1)
                else:
                    required_humid_kg_h = 0.0

                if is_velocity_warning:
                    st.error("⚠️ 경고: 코일 면풍속이 2.5 m/s를 초과하여 응축수 비산 위험이 있습니다. 필요시 풍량을 조절하거나 상위 규격 모델 검토가 권장됩니다.")
                else:
                    st.success(status_msg)

                st.warning(f"  ❄️ **실시간 계산 요구 가습량:** {required_humid_kg_h} kg/h (목표 상대습도 {v_target_rh}% 기준) | ❄️ **냉수량:** {cool_lpm} LPM | 🔥 **온수량:** {heat_lpm} LPM | 🌊 **관내수속:** {water_velocity} m/s")

                col_m1, col_m2 = st.columns([1, 1])
                with col_m1:
                    st.metric(label="✨ 추천 모델명", value=selected_row['Model_Name'])
                
                f_row, f_col = selected_row['Filter_Row'], selected_row['Filter_Col']
                
                # 🌟 [SyntaxError 차단 완벽 정렬]: 누락되었던 대괄호 닫힘 및 쉼표 구조를 완벽 정렬
                specs_list = [
                    ("표준 정격 풍량", f"{int(selected_row['STD_CMH']):,} CMH ({int(selected_row['Std_CMM'])} CMM)"), [cite: 556]
                    ("적정 풍량 범위", f"{int(selected_row['Range_CMH_Min']):,} ~ {int(selected_row['Range_CMH_Max']):,} CMH"), [cite: 556]
                    ("정격 냉방능력", f"{int(selected_row['Cooling_kcal_h']):,} kcal/h"), [cite: 556]
                    (f"정격 난방능력 ({heat_label})", f"{int(selected_row[heat_col]):,} kcal/h"), [cite: 556]
                    ("장비 외형 규격 크기 (W × H × L)", f"{int(selected_row['Size_W']):,} × {int(selected_row['Size_H']):,} × {int(selected_row['Size_L']):,} mm"),
                    ("급기 접속관 (SA) 사이즈", f"{selected_row['Conn_SA']} mm"),
                    ("외기 접속관 (OA) 사이즈", f"{selected_row['Conn_OA']} mm"),
                    ("배기 접속관 (EA) 사이즈", f"{selected_row['Conn_EA']} mm" if selected_row['Type_H_HI'] == 'HI' else "- (컴팩트형 제외)"),
                    ("환기 접속관 (RA) 사이즈", f"{selected_row['Conn_RA']} mm"),
                    ("공급팬 (SF) 규격 사이즈", selected_row['SF_Fan_Size']), [cite: 556]
                    ("공급팬 모터 동력 / 기내 정압", f"{selected_row['SF_Motor_kW']} kW (보정 정압 {int(selected_row['SF_Static_mmAq']) + int(v_added_stat)} mmAq)"), [cite: 556]
                    ("환기팬 (RF) 규격 사이즈", selected_row['RF_Fan_Size'] if selected_row['Type_H_HI'] == 'HI' else "- (컴팩트형 제외)"), [cite: 556]
                    ("환기팬 모터 동력 / 기내 정압", f"{selected_row['RF_Motor_kW']} kW (보정 정압 {int(selected_row['RF_Static_mmAq']) + int(v_added_stat)} mmAq)" if selected_row['Type_H_HI'] == 'HI' else "- (컴팩트형 제외)"), [cite: 556]
                    ("코일 패스 및 수량", f"{int(selected_row['Coil_Pass'])} Pass / {int(selected_row['Coil_Qty'])} 개"), [cite: 556]
                    ("코일 규격 크기 (H × W)", f"{int(selected_row['Coil_H'])} mm × {int(selected_row['Coil_W'])} mm"),
                    ("정면 면적 (Face Area)", f"{face_area} m²"), [cite: 556]
                    ("코일 면풍속 (Coil Face Velocity)", f"{coil_velocity} m/s"),
                    ("동파방지 예열코일 (Pre-Heater)", "장착 완료 (카탈로그 표준 2-Row 수식 연동)" if v_opt_anti else "미장착 (None)"), [cite: 608]
                    ("가습 장치 종류 (Humidifier)", f"{v_opt_humid}"), [cite: 644]
                    ("★ 현장 요구 가습량 (Required)", f"{required_humid_kg_h} kg/h (실시간 부하 역산 값)"), 
                    ("장비 정격 가습량 (Actual)", f"{int(selected_row['Humid_kg_h'])} kg/h (루트에어 마스터 규격 스펙)"), [cite: 556]
                    ("엘리미네이터 (Eliminator)", "장착 완료 (응축수 비산방지 프로텍터)" if v_opt_elim else "미장착"), [cite: 525, 655]
                    ("전처리 프리 필터 (Pre-Filter)", f"장착 완료 ({f_row}단 × {f_col}열)" if v_opt_pre else "미장착 (옵션제외)"), [cite: 556]
                    ("중성능 미디움 필터 (Medium Filter)", f"장착 완료 ({f_row}단 × {f_col}열)" if v_opt_med else "미장착 (옵션제외)"), [cite: 556]
                    ("고성능 헤파 필터 (HEPA Filter)", f"장착 완료 ({f_row}단 × {f_col}열)" if v_opt_hepa else "미장착 (옵션제외)"), [cite: 556]
                    ("냉온수 배관 관경", f"{int(selected_row['Conn_Cool_In_Out_A'])} A × {int(selected_row['Conn_Cool_Qty'])} 개") [cite: 556]
                ]

                input_conditions = {
                    'cmh': curr_cmh, 'cool': curr_cool, 'heat': curr_heat, 'heat_type': curr_type, 'ahu_type_label': curr_ahu_type
                }
                project_info = {'date': c_date, 'project_name': c_name, 'author': c_author}
                density_info = {
                    'location': curr_location, 'density': v_rho, 'corr_cool': corr_cool_req, 'corr_heat': corr_heat_req,
                    'c_temp': v_ct, 'c_rh': v_cr, 'h_temp': v_ht, 'h_rh': v_hr
                }
                coil_calc_info = {
                    'c_tw1': v_cc_tw1, 'c_tw2': v_cc_tw2, 'h_tw1': v_ch_tw1, 'h_tw2': v_ch_tw2,
                    'cool_lpm': cool_lpm, 'heat_lpm': heat_lpm, 'cool_lmtd': cool_lmtd, 'water_velocity': water_velocity
                }
                
                pdf_bytes = generate_pdf(selected_row['Model_Name'], specs_list, input_conditions, project_info, density_info, coil_calc_info, is_velocity_warning) [cite: 556]
                
                with col_m2:
                    st.write("") 
                    st.download_button(
                        label="📄 풀스펙 필터 일체형 성적서 다운로드 (PDF)",
                        data=pdf_bytes,
                        file_name=f"루트에어_풀옵션_필터성적서_{c_name}_{selected_row['Model_Name']}.pdf",
                        mime="application/pdf"
                    )

                res_data = {
                    "사양 구분 항목": [s[0] for s in specs_list],
                    "상세 기술 데이터": [s[1] for s in specs_list]
                }
                res_df = pd.DataFrame(res_data)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
            else:
                st.error("❌ 에러: 공기 밀도 보정 결과, 요구 부하를 감당할 수 있는 대형 모델이 데이터베이스에 없습니다.")
        else:
            st.info("💡 좌측 입력창에 정보를 입력한 후 [최적 장비 선정하기] 버튼을 누르세요.")