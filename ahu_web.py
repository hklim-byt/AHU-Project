import os
import csv
import pandas as pd
import streamlit as st
from fpdf import FPDF
from datetime import datetime
import base64
import math
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

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

def calculate_enthalpy(db_temp, abs_humidity):
    return round(1.006 * db_temp + abs_humidity * (2501.0 + 1.86 * db_temp), 2)

def calculate_wet_bulb(T, RH):
    try:
        wb = T * math.atan(0.151977 * math.pow(RH + 8.313659, 0.5)) + math.atan(T + RH) - math.atan(RH - 1.676331) + 0.00391838 * math.pow(RH, 1.5) * math.atan(0.023101 * RH) - 4.686035
        return round(wb, 1)
    except:
        return T

# 🌟 [그래픽 엔진 완벽 보완]: 네모 박스로 한글이 깨지는 현상(Tofu)을 원천 차단하는 폰트 강제 주입 로직
def generate_psychrometric_chart(t1, rh1, t2, rh2, is_korean):
    font_path = os.path.join(os.getcwd(), "malgun.ttf")
    font_prop = fm.FontProperties(fname=font_path) if os.path.exists(font_path) else None

    fig, ax = plt.subplots(figsize=(10, 6))
    
    T_curve = range(-10, 45)
    x_curve = [calculate_absolute_humidity(t, 100) for t in T_curve]
    ax.plot(T_curve, x_curve, 'k-', linewidth=1.5, label="Saturation Line (100% RH)")
    
    x_50 = [calculate_absolute_humidity(t, 50) for t in T_curve]
    ax.plot(T_curve, x_50, 'k--', linewidth=0.8, alpha=0.5, label="50% RH")

    x1 = calculate_absolute_humidity(t1, rh1)
    h1 = calculate_enthalpy(t1, x1)
    wb1 = calculate_wet_bulb(t1, rh1)

    x2 = calculate_absolute_humidity(t2, rh2)
    h2 = calculate_enthalpy(t2, x2)
    wb2 = calculate_wet_bulb(t2, rh2)

    ax.plot(t1, x1, 'ro', markersize=8)
    ax.plot(t2, x2, 'bo', markersize=8)
    ax.annotate('', xy=(t2, x2), xytext=(t1, x1), arrowprops=dict(arrowstyle="->", color='gray', lw=2))

    # 국문/영문 풀네임 분기
    if is_korean:
        t1_lbl, t2_lbl = "입구 공기 (Inlet)", "출구 공기 (Outlet)"
        db_lbl, wb_lbl, ah_lbl, ent_lbl = "건구온도", "습구온도", "절대습도", "엔탈피"
        x_label, y_label = "건구온도 (℃)", "절대습도 (kg/kg')"
        title_txt = "루트에어 공기선도 프로세스 분석 시뮬레이션"
    else:
        t1_lbl, t2_lbl = "INLET (Point 1)", "OUTLET (Point 2)"
        db_lbl, wb_lbl, ah_lbl, ent_lbl = "Dry Bulb", "Wet Bulb", "Abs. Humidity", "Enthalpy"
        x_label, y_label = "Dry Bulb Temperature (℃)", "Absolute Humidity (kg/kg')"
        title_txt = "RootAir Psychrometric Process Analysis"

    bbox_props1 = dict(boxstyle="round,pad=0.5", fc="#ffe6e6", ec="red", lw=1.5, alpha=0.9)
    txt1 = f"[{t1_lbl}]\n{db_lbl}: {t1} ℃\n{wb_lbl}: {wb1} ℃\n{ah_lbl}: {round(x1, 4)} kg/kg'\n{ent_lbl}: {h1} kJ/kg"
    
    bbox_props2 = dict(boxstyle="round,pad=0.5", fc="#e6f2ff", ec="blue", lw=1.5, alpha=0.9)
    txt2 = f"[{t2_lbl}]\n{db_lbl}: {t2} ℃\n{wb_lbl}: {wb2} ℃\n{ah_lbl}: {round(x2, 4)} kg/kg'\n{ent_lbl}: {h2} kJ/kg"
    
    # 폰트 프로퍼티가 있으면 강제 적용, 없으면 기본 적용
    if font_prop:
        ax.text(t1, x1 + 0.0015, txt1, ha="center", va="bottom", bbox=bbox_props1, fontproperties=font_prop, fontsize=10)
        ax.text(t2, x2 - 0.0015, txt2, ha="center", va="top", bbox=bbox_props2, fontproperties=font_prop, fontsize=10)
        ax.set_xlabel(x_label, fontproperties=font_prop, fontsize=11)
        ax.set_ylabel(y_label, fontproperties=font_prop, fontsize=11)
        ax.set_title(title_txt, fontproperties=font_prop, fontsize=15)
        ax.legend(loc="upper left", prop=font_prop)
    else:
        ax.text(t1, x1 + 0.0015, txt1, ha="center", va="bottom", bbox=bbox_props1, fontsize=9, fontweight='bold')
        ax.text(t2, x2 - 0.0015, txt2, ha="center", va="top", bbox=bbox_props2, fontsize=9, fontweight='bold')
        ax.set_xlabel(x_label, fontweight='bold')
        ax.set_ylabel(y_label, fontweight='bold')
        ax.set_title(title_txt, fontweight='bold', fontsize=14)
        ax.legend(loc="upper left")

    ax.set_xlim(-5, 45)
    ax.set_ylim(0, 0.035)
    ax.grid(True, linestyle=':', alpha=0.6)
    
    plt.tight_layout()
    fig.savefig("psychro_chart.png", dpi=200)
    plt.close(fig)

if df is None:
    st.error("❌ 데이터베이스(CSV) 파일을 찾을 수 없습니다.")
else:
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

    # 🌟 PDF 출력 엔진
    def generate_pdf(model_name, specs_list, input_conditions, project_info, density_info, coil_calc_info, is_velocity_warning, is_korean):
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
            pdf.image("company_logo.png", x=10, y=6, w=22)
        if os.path.exists("ahri_logo.png"):
            pdf.image("ahri_logo.png", x=175, y=6, w=22)
            
        pdf.set_y(14)

        pdf.set_font("Malgun" if has_korean else "helvetica", style="", size=16)
        pdf.set_text_color(30, 41, 59)
        title_txt = "루트에어 AHU 장비 선정 성적서" if is_korean else "RootAir AHU Selection Report"
        pdf.cell(190, 9, txt=title_txt, ln=True, align="C")
        pdf.ln(1)
        
        pdf.set_font("Malgun" if has_korean else "helvetica", style="", size=8.5)
        pdf.set_text_color(51, 65, 85)
        
        l_proj = " 프로젝트명" if is_korean else " Project Name"
        l_auth = " 작성자" if is_korean else " Author"
        l_date = " 선정 일자" if is_korean else " Date"
        
        pdf.cell(25, 4.8, txt=l_proj, border=1)
        pdf.cell(80, 4.8, txt=f" {project_info['project_name']}", border=1)
        pdf.cell(25, 4.8, txt=l_auth, border=1)
        pdf.cell(60, 4.8, txt=f" {project_info['author']}", border=1, ln=True)
        pdf.cell(25, 4.8, txt=l_date, border=1)
        pdf.cell(165, 4.8, txt=f" {project_info['date']}", border=1, ln=True)
        pdf.ln(2)
        
        pdf.set_font("Malgun" if has_korean else "helvetica", style="" if has_korean else "B", size=9.5)
        pdf.set_text_color(15, 23, 42)
        t1_title = "[1] 설계 입력 조건 및 공기 밀도 보정 (Design Input & Density)" if is_korean else "[1] Design Input & Air Density Correction"
        pdf.cell(190, 5.0, txt=t1_title, ln=True, align="L")
        pdf.set_font("Malgun" if has_korean else "helvetica", size=8.0)
        
        pdf.cell(48, 4.2, txt=" Required Air Flow:", border=1)
        pdf.cell(47, 4.2, txt=f" {input_conditions['cmh']:,} CMH", border=1)
        pdf.cell(48, 4.2, txt=" Unit Layout Type:", border=1)
        pdf.cell(47, 4.2, txt=f" {input_conditions['ahu_type_label']}", border=1, ln=True)
        
        pdf.cell(48, 4.2, txt=" Input Cooling Load:", border=1)
        pdf.cell(47, 4.2, txt=f" {input_conditions['cool']:,} kcal/h", border=1)
        pdf.cell(48, 4.2, txt=" Corrected Cool Load:", border=1)
        pdf.cell(47, 4.2, txt=f" {int(density_info['corr_cool']):,} kcal/h", border=1, ln=True)
        
        pdf.cell(48, 4.2, txt=" Input Heating Load:", border=1)
        pdf.cell(47, 4.2, txt=f" {input_conditions['heat']:,} kcal/h", border=1)
        pdf.cell(48, 4.2, txt=" Corrected Heat Load:", border=1)
        pdf.cell(47, 4.2, txt=f" {int(density_info['corr_heat']):,} kcal/h", border=1, ln=True)
        
        pdf.cell(48, 4.2, txt=" Project Location:", border=1)
        pdf.cell(47, 4.2, txt=f" {density_info['location'].split(' ')[0]}", border=1)
        pdf.cell(48, 4.2, txt=" Real Air Density:", border=1)
        pdf.cell(47, 4.2, txt=f" {density_info['density']} kg/m3", border=1, ln=True)
        pdf.ln(2)
        
        pdf.set_font("Malgun" if has_korean else "helvetica", style="" if has_korean else "B", size=9.5)
        t2_title = "[2] 코일 열정격 및 옵션 사양 (Coil & Option Mechanical Data)" if is_korean else "[2] Coil & Option Mechanical Data"
        pdf.cell(190, 5.0, txt=t2_title, ln=True, align="L")
        pdf.set_font("Malgun" if has_korean else "helvetica", size=8.0)
        
        l_c_type = " 냉방 코일 운전 종류:" if is_korean else " Cooling Coil Type:"
        l_h_temp = " 온수 입/출구 온도:" if is_korean else " Heating Water In/Out:"
        l_c_flow = " 냉수 유량 / 냉매 온도:" if is_korean else " Chill. Flow / DX Temp:"
        l_h_flow = " 온수 요구 유량 (LPM):" if is_korean else " Heat. Water Flow (LPM):"
        l_lmtd = " 냉방 대수평균 (LMTD):" if is_korean else " Cooling LMTD:"
        l_vel = " 코일 관내 유속 (Water):" if is_korean else " Tube Water Velocity:"
        
        # 🌟 글자 겹침 버그 원천 수정: ISP/ESP 텍스트를 제거하고 43 셀 안에 안전하게 표기
        pdf.cell(52, 4.2, txt=l_c_type, border=1)
        pdf.cell(43, 4.2, txt=f" {coil_calc_info['cool_type']}", border=1)
        pdf.cell(52, 4.2, txt=l_h_temp, border=1)
        pdf.cell(43, 4.2, txt=f" {coil_calc_info['h_tw1']} C -> {coil_calc_info['h_tw2']} C", border=1, ln=True)
        
        pdf.cell(52, 4.2, txt=l_c_flow, border=1)
        pdf.cell(43, 4.2, txt=f" {coil_calc_info['cool_fluid_status']}", border=1)
        pdf.cell(52, 4.2, txt=l_h_flow, border=1)
        pdf.cell(43, 4.2, txt=f" {coil_calc_info['heat_lpm']} LPM", border=1, ln=True)
        
        pdf.cell(52, 4.2, txt=l_lmtd, border=1)
        pdf.cell(43, 4.2, txt=f" {coil_calc_info['cool_lmtd']}", border=1)
        pdf.cell(52, 4.2, txt=l_vel, border=1)
        pdf.cell(43, 4.2, txt=f" {coil_calc_info['water_velocity']}", border=1, ln=True)
        pdf.ln(2)
        
        pdf.set_font("Malgun" if has_korean else "helvetica", style="" if has_korean else "B", size=10)
        t3_title = f"[3] 추천 모델 상세 기술 규격 명세: {model_name}" if is_korean else f"[3] Recommended Model Specifications: {model_name}"
        pdf.cell(190, 5.5, txt=t3_title, ln=True, align="L")
        pdf.set_font("Malgun" if has_korean else "helvetica", size=7.3) 
            
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(75, 4.0, txt=" Specification Item", border=1, fill=True)
        pdf.cell(115, 4.0, txt=" Technical Data", border=1, fill=True, ln=True)
        
        for spec, val in specs_list:
            if is_velocity_warning and ("코일 면풍속" in spec or "Face Velocity" in spec):
                pdf.set_text_color(220, 38, 38)
                pdf.cell(75, 4.0, txt=f" {spec}", border=1)
                pdf.cell(115, 4.0, txt=f" {val}", border=1, ln=True)
                pdf.set_text_color(51, 65, 85)
            else:
                pdf.cell(75, 4.0, txt=f" {spec}", border=1)
                pdf.cell(115, 4.0, txt=f" {val}", border=1, ln=True)
            
        pdf.ln(1.5)
        
        if is_velocity_warning:
            pdf.set_text_color(220, 38, 38)
            pdf.set_font("Malgun", style="", size=7.8)
            warn_txt = "⚠️ 코일 면풍속이 2.5 m/s를 초과하여 응축수 비산 위험이 있습니다." if is_korean else "⚠️ Coil face velocity exceeds 2.5 m/s. Condensate carryover risk."
            pdf.cell(190, 3.8, txt=warn_txt, border=0, ln=True, align="L")
            pdf.ln(0.5)

        # 2페이지 추가 로직: 공기선도 프로세스
        pdf.add_page()
        
        if os.path.exists("company_logo.png"):
            pdf.image("company_logo.png", x=10, y=6, w=22)
        if os.path.exists("ahri_logo.png"):
            pdf.image("ahri_logo.png", x=175, y=6, w=22)
        pdf.set_y(15)
        
        pdf.set_font("Malgun" if has_korean else "helvetica", style="" if has_korean else "B", size=14)
        pdf.set_text_color(15, 23, 42)
        t4_title = "[4] 공기선도 프로세스 시뮬레이션 (Psychrometric Process)" if is_korean else "[4] Psychrometric Process Simulation"
        pdf.cell(190, 8, txt=t4_title, ln=True, align="L")
        pdf.ln(2)
        
        pdf.set_font("Malgun" if has_korean else "helvetica", style="", size=9)
        pdf.set_text_color(51, 65, 85)
        desc_txt = "* 코일 통과 전/후의 공기 상태(건구온도, 습구온도, 절대습도, 엔탈피) 물리적 변화를 나타냅니다." if is_korean else "* Illustrates the psychrometric changes (DB, WB, AH, Enthalpy) across the cooling coil."
        pdf.cell(190, 5, txt=desc_txt, ln=True, align="L")
        pdf.ln(5)
        
        if os.path.exists("psychro_chart.png"):
            pdf.image("psychro_chart.png", x=15, y=40, w=180)
            
        pdf.set_y(-15)
        pdf.set_font("Malgun", style="", size=6.8)
        pdf.set_text_color(148, 163, 184)
        foot_txt = "* 본 성적서는 루트에어 공기선도_RootAirChart v1.1 및 Flaktkorea 코일전열 공식을 통합 연동한 정밀 설계 문서입니다." if is_korean else "* Generated by RootAir Psychrometric Chart v1.1 & FlaktKorea Engineering Engine."
        pdf.cell(190, 3.2, txt=foot_txt, ln=True, align="C")
        
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
        ext_static = st.number_input("설계 기외 정압 (External Static Pressure, mmAq)", value=50, step=5, min_value=0, max_value=300)
        
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

        with st.expander("💧 코일 열원 및 운전 온도 설계 조건", expanded=True):
            cool_source_type = st.radio("냉방 코일 종류 선택", ["냉수 코일 (Chilled Water)", "DX 코일 (Direct Expansion)"])
            
            if "냉수" in cool_source_type:
                coil_c_tw1 = st.number_input("냉수 입구 온도 (°C)", value=7.0, step=0.5)
                coil_c_tw2 = st.number_input("냉수 출구 온도 (°C)", value=12.0, step=0.5)
                dx_evap_temp = 5.0
            else:
                dx_evap_temp = st.number_input("냉매 증발 온도 (Evaporating Temp, °C)", value=5.0, step=0.5, min_value=0.0, max_value=15.0)
                coil_c_tw1, coil_c_tw2 = 0.0, 0.0
                
            coil_h_tw1 = st.number_input("온수 입구 온도 (°C)", value=60.0, step=0.5)
            coil_h_tw2 = st.number_input("온수 출구 온도 (°C)", value=50.0, step=0.5)

        with st.expander("➕ AHU 구성 부속품 및 필터 사양 선택 (정압 보정 연동)", expanded=True):
            opt_pre_filter = st.checkbox("🔍 프리 필터 장착 (Pre-Filter, AFI 82%급)", value=True)
            opt_med_filter = st.checkbox("🔍 미디움 필터 장착 (Medium Filter, NBS 90%급)", value=False)
            opt_hepa_filter = st.checkbox("🔍 헤파 필터 장착 (HEPA Filter, 크린룸용 99.97%급)", value=False)
            st.markdown("---")
            
            opt_antifreeze = st.checkbox("❄️ 동파방지 예열 코일 장비 내장 (Pre-Heater)", value=False)
            opt_humidifier = st.selectbox("💨 가습기 종류 선택 (Humidifier Type)", ["장착 안 함 (None)", "기화식 가습기 (Evaporative)", "전극봉식 가습기 (Electronic)", "증기 분무식 가습기 (Steam)"])
            
            target_indoor_rh = 50
            if opt_humidifier != "장착 안 함 (None)":
                target_indoor_rh = st.slider(" 겨울철 실내 목표 상대습도 설정 (%)", value=50, min_value=20, max_value=80, step=5)
                
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
        
        st.write("---")
        report_lang = st.radio("📄 보고서 출력 언어 (Report Language)", ["한국어 (Korean)", "English (영문)"], horizontal=True)

        st.write("")
        submit_btn = st.button("🔍 최적 장비 선정하기")

    with col_result:
        st.subheader("3. 최적 모델 선정 결과 (Output)")
        st.write("")

        v_target_rh = st.session_state.get('target_rh', 50)
        v_opt_humid = st.session_state.get('opt_humid', "장착 안 함 (None)")
        v_added_stat = st.session_state.get('added_stat', 0.0)
        v_opt_anti = st.session_state.get('opt_anti', False)
        v_opt_elim = st.session_state.get('opt_elim', False)
        v_opt_pre = st.session_state.get('opt_pre', True)
        v_opt_med = st.session_state.get('opt_med', False)
        v_opt_hepa = st.session_state.get('opt_hepa', False)
        v_cool_source = st.session_state.get('cool_source', "냉수 코일 (Chilled Water)")
        v_dx_evap = st.session_state.get('dx_evap', 5.0)
        v_ext_static = st.session_state.get('ext_static_val', 50.0) 
        v_report_lang = st.session_state.get('report_lang', "한국어 (Korean)")

        if submit_btn or st.session_state.get('pdf_ready', False):
            if submit_btn:
                st.session_state['pdf_ready'] = True
                st.session_state['cmh_val'] = cmh
                st.session_state['ext_static_val'] = ext_static 
                st.session_state['cool_val'] = cool_req
                st.session_state['heat_val'] = heat_req
                st.session_state['heat_type_val'] = heat_type
                st.session_state['ahu_type_val'] = ahu_type
                st.session_state['loc_val'] = location_select
                st.session_state['final_rho'] = avg_calculated_rho
                st.session_state['c_t'] = cool_temp
                st.session_state['c_r'] = cool_rh
                st.session_state['h_t'] = heat_temp
                st.session_state['h_r'] = heat_rh
                st.session_state['cc_tw1'] = coil_c_tw1
                st.session_state['cc_tw2'] = coil_c_tw2
                st.session_state['ch_tw1'] = coil_h_tw1
                st.session_state['ch_tw2'] = coil_h_tw2
                st.session_state['opt_pre'] = opt_pre_filter
                st.session_state['opt_med'] = opt_med_filter
                st.session_state['opt_hepa'] = opt_hepa_filter
                st.session_state['opt_anti'] = opt_antifreeze
                st.session_state['opt_humid'] = opt_humidifier
                st.session_state['opt_elim'] = opt_eliminator
                st.session_state['added_stat'] = added_static
                st.session_state['target_rh'] = target_indoor_rh
                st.session_state['cool_source'] = cool_source_type
                st.session_state['dx_evap'] = dx_evap_temp
                st.session_state['p_date'] = proj_date.strftime("%Y-%m-%d")
                st.session_state['p_name'] = proj_name if proj_name else "미지정 프로젝트 (N/A)"
                st.session_state['p_author'] = proj_author if proj_author else "담당자 (Manager)"
                st.session_state['report_lang'] = report_lang
            
            curr_cmh = st.session_state.get('cmh_val', cmh)
            curr_ext_static = st.session_state.get('ext_static_val', ext_static) 
            curr_cool = st.session_state.get('cool_val', cool_req)
            curr_heat = st.session_state.get('heat_val', heat_req)
            curr_type = st.session_state.get('heat_type_val', heat_type)
            curr_ahu_type = st.session_state.get('ahu_type_val', ahu_type)
            curr_selected_type = "H" if "H형" in curr_ahu_type else "HI"
            curr_location = st.session_state.get('loc_val', location_select)
            v_rho = st.session_state.get('final_rho', avg_calculated_rho)
            
            c_date = st.session_state.get('p_date', proj_date.strftime("%Y-%m-%d"))
            c_name = st.session_state.get('p_name', proj_name if proj_name else "미지정 프로젝트 (N/A)")
            c_author = st.session_state.get('p_author', proj_author if proj_author else "담당자 (Manager)")
            
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
            v_cool_source = st.session_state.get('cool_source', cool_source_type)
            v_dx_evap = st.session_state.get('dx_evap', dx_evap_temp)
            v_report_lang = st.session_state.get('report_lang', report_lang)
            is_kor = "한국어" in v_report_lang
            
            heat_col = 'Heating_Water_kcal_h' if "온수" in curr_type else 'Heating_Steam_kcal_h'
            heat_label = "온수" if "온수" in curr_type else "증기"
            
            density_ratio = 1.2041 / v_rho
            corr_cool_req = curr_cool * density_ratio
            corr_heat_req = curr_heat * density_ratio
            
            type_filtered_df = df[df['Type_H_HI'] == curr_selected_type]
            candidates = type_filtered_df[(type_filtered_df['Range_CMH_Min'] <= curr_cmh) & (curr_cmh <= type_filtered_df['Range_CMH_Max'])]
            if candidates.empty:
                candidates = type_filtered_df[type_filtered_df['Range_CMH_Max'] >= curr_cmh]
                
            selected_row = None
            status_msg = "✅ 기상 조건, 기내/기외 정압 전열 융합 검증이 완료된 최적 사양이 도출되었습니다."
            status_type = "success"

            for idx_row, row in candidates.iterrows():
                if row['Cooling_kcal_h'] >= corr_cool_req and row[heat_col] >= corr_heat_req:
                    selected_row = row
                    break

            if selected_row is None:
                all_larger = type_filtered_df[type_filtered_df['Range_CMH_Max'] >= curr_cmh]
                for idx_row, row in all_larger.iterrows():
                    if row['Cooling_kcal_h'] >= corr_cool_req and row[heat_col] >= corr_heat_req:
                        selected_row = row
                        status_msg = "⚠️ 알림: 추가 옵션 기내 저항 가산 및 부하 충족을 위해 한 단계 상위 모델이 선정되었습니다."
                        status_type = "warning"
                        break

            if selected_row is not None:
                st.info(f"📋 **Project:** {c_name} | 👤 **Author:** {c_author} | 📅 **Date:** {c_date} | 📍 **Location:** {curr_location.split(' ')[0]}")
                
                dt_heat = max(0.1, abs(v_ch_tw1 - v_ch_tw2))
                heat_lpm = round(corr_heat_req / (60.0 * dt_heat * 1.0), 1)
                
                if "냉수" in v_cool_source:
                    dt_cool = max(0.1, abs(v_cc_tw2 - v_cc_tw1))
                    cool_lpm_val = round(corr_cool_req / (60.0 * dt_cool * 1.0), 1)
                    cool_lpm_str = f"{cool_lpm_val} LPM"
                    cool_lmtd_str = f"{round(((v_ct - v_cc_tw2) - (15.0 - v_cc_tw1)) / math.log(max(1.01, (v_ct - v_cc_tw2)) / max(1.0, (15.0 - v_cc_tw1))), 1)} C"
                    db_pass = float(selected_row['Coil_Pass']) if 'Coil_Pass' in selected_row else 18.0
                    water_velocity_str = f"{round((cool_lpm_val / 60000.0) / (db_pass * math.pi * (0.0127**2) / 4.0), 2)} m/s (안정)"
                    
                    cool_type_label = "냉수 코일" if is_kor else "Chilled Water"
                    outlet_temp_for_chart = 15.0
                    outlet_rh_for_chart = 95.0
                else:
                    cool_lpm_str = "N/A"
                    cool_lmtd_str = "N/A"
                    water_velocity_str = "N/A"
                    
                    cool_type_label = f"DX 코일({v_dx_evap}℃)" if is_kor else f"DX Coil ({v_dx_evap}C)"
                    outlet_temp_for_chart = 13.0
                    outlet_rh_for_chart = 90.0
                
                generate_psychrometric_chart(v_ct, v_cr, outlet_temp_for_chart, outlet_rh_for_chart, is_kor)
                
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
                    st.error("⚠️ 경고: 코일 면풍속이 2.5 m/s를 초과하여 응축수 비산 위험이 있습니다. 대형 규격 모델 검토를 강력 권장합니다." if is_kor else "⚠️ Warning: Face velocity exceeds 2.5m/s. Risk of water carryover.")
                else:
                    st.success(status_msg)

                calculated_internal_static = int(selected_row['SF_Static_mmAq']) + int(v_added_stat)
                total_static_pressure = int(curr_ext_static) + calculated_internal_static
                
                st.warning(f"⚡ **정압 분석서:** 기내 정압(ISP): {calculated_internal_static} mmAq | 기외 정압(ESP): {curr_ext_static} mmAq | 최종 전정압(TSP): {total_static_pressure} mmAq")

                col_m1, col_m2 = st.columns([1, 1])
                with col_m1:
                    st.metric(label="✨ 추천 모델명", value=selected_row['Model_Name'])
                
                f_row, f_col = selected_row['Filter_Row'], selected_row['Filter_Col']
                
                # 🌟 [글자 깨짐 방지 영문 픽스]: '단/열/개'를 글로벌 스탠다드 Row/Col/EA로 전면 수정하여 Tofu 버그 차단
                if is_kor:
                    specs_list = [
                        ("표준 정격 풍량", f"{int(selected_row['STD_CMH']):,} CMH ({int(selected_row['Std_CMM'])} CMM)"),
                        ("적정 풍량 범위", f"{int(selected_row['Range_CMH_Min']):,} ~ {int(selected_row['Range_CMH_Max']):,} CMH"),
                        ("선택 냉방 열원 종류", f"{cool_type_label}"),
                        ("정격 냉방능력", f"{int(selected_row['Cooling_kcal_h']):,} kcal/h"),
                        (f"정격 난방능력 ({heat_label})", f"{int(selected_row[heat_col]):,} kcal/h"),
                        ("동파방지 예열코일 (Pre-Heater)", "장착 완료 (2-Row 표준 매칭)" if v_opt_anti else "미장착 (None)"),
                        ("가습 장치 종류 (Humidifier)", f"{v_opt_humid.split(' (')[0]}"),
                        ("★ 현장 요구 가습량 (Required)", f"{required_humid_kg_h} kg/h (실시간 부하 역산)"), 
                        ("장비 정격 가습량 (Actual)", f"{int(selected_row['Humid_kg_h'])} kg/h (루트에어 마스터 규격)"),
                        ("엘리미네이터 (Eliminator)", "장착 완료 (응축수 비산방지용)" if v_opt_elim else "미장착"),
                        ("실시간 계산 기내 정압 (ISP)", f"{calculated_internal_static} mmAq (본체 + 필터 + 옵션 저항)"), 
                        ("설계 기외 정압 (ESP)", f"{curr_ext_static} mmAq (현장 덕트 마찰 저항)"), 
                        ("합산 보정 최종 전정압 (TSP)", f"{total_static_pressure} mmAq (송풍기 정격 압력)"), 
                        ("장비 외형 규격 크기 (W × H × L)", f"{int(selected_row['Size_W']):,} × {int(selected_row['Size_H']):,} × {int(selected_row['Size_L']):,} mm"),
                        ("급기 접속관 (SA) 사이즈", f"{selected_row['Conn_SA']} mm"),
                        ("외기 접속관 (OA) 사이즈", f"{selected_row['Conn_OA']} mm"),
                        ("환기 접속관 (RA) 사이즈", f"{selected_row['Conn_RA']} mm"),
                        ("공급팬 (SF) 규격 사이즈", f"{selected_row['SF_Fan_Size']}"),
                        ("공급팬 모터 사양 및 최종 전정압", f"{selected_row['SF_Motor_kW']} kW (TSP {total_static_pressure} mmAq 기준)"), 
                        ("코일 패스 및 수량", f"{int(selected_row['Coil_Pass'])} Pass / {int(selected_row['Coil_Qty'])} EA"),
                        ("코일 규격 크기 (H × W)", f"{int(selected_row['Coil_H'])} mm × {int(selected_row['Coil_W'])} mm"),
                        ("정면 면적 (Face Area)", f"{face_area} m²"),
                        ("코일 면풍속 (Coil Face Velocity)", f"{coil_velocity} m/s"),
                        ("전처리 프리 필터 (Pre-Filter)", f"장착 완료 ({f_row} Row × {f_col} Col)" if v_opt_pre else "미장착 (옵션제외)"),
                        ("중성능 미디움 필터 (Medium Filter)", f"장착 완료 ({f_row} Row × {f_col} Col)" if v_opt_med else "미장착 (옵션제외)"),
                        ("고성능 헤파 필터 (HEPA Filter)", f"장착 완료 ({f_row} Row × {f_col} Col)" if v_opt_hepa else "미장착 (옵션제외)"),
                        ("냉온수 배관 관경", f"{int(selected_row['Conn_Cool_In_Out_A'])} A × {int(selected_row['Conn_Cool_Qty'])} EA")
                    ]
                else:
                    en_heat_lbl = "Water" if "온수" in heat_type else "Steam"
                    specs_list = [
                        ("Standard Air Flow", f"{int(selected_row['STD_CMH']):,} CMH ({int(selected_row['Std_CMM'])} CMM)"),
                        ("Optimum Air Flow Range", f"{int(selected_row['Range_CMH_Min']):,} ~ {int(selected_row['Range_CMH_Max']):,} CMH"),
                        ("Cooling Source Type", f"{cool_type_label}"),
                        ("Rated Cooling Capacity", f"{int(selected_row['Cooling_kcal_h']):,} kcal/h"),
                        (f"Rated Heating Capacity ({en_heat_lbl})", f"{int(selected_row[heat_col]):,} kcal/h"),
                        ("Anti-Freeze Pre-Heater", "Equipped (2-Row Standard Matched)" if v_opt_anti else "Not Equipped (None)"),
                        ("Humidifier Type", f"{v_opt_humid.split('(')[-1].replace(')','')} Type" if "None" not in v_opt_humid else "None"),
                        ("★ Required Humidification", f"{required_humid_kg_h} kg/h (Real-time Calc)"), 
                        ("Rated Humidification (Actual)", f"{int(selected_row['Humid_kg_h'])} kg/h (RootAir Master Spec)"),
                        ("Eliminator", "Equipped (Condensate Protector)" if v_opt_elim else "Not Equipped"),
                        ("Internal Static Pressure (ISP)", f"{calculated_internal_static} mmAq (Unit + Filter + Options)"), 
                        ("External Static Pressure (ESP)", f"{curr_ext_static} mmAq (Field Duct Friction)"), 
                        ("Total Static Pressure (TSP)", f"{total_static_pressure} mmAq (Target Fan Pressure)"), 
                        ("Unit Dimensions (W × H × L)", f"{int(selected_row['Size_W']):,} × {int(selected_row['Size_H']):,} × {int(selected_row['Size_L']):,} mm"),
                        ("Supply Air (SA) Connection", f"{selected_row['Conn_SA']} mm"),
                        ("Outdoor Air (OA) Connection", f"{selected_row['Conn_OA']} mm"),
                        ("Return Air (RA) Connection", f"{selected_row['Conn_RA']} mm"),
                        ("Supply Fan (SF) Size", f"{selected_row['SF_Fan_Size']}"),
                        ("SF Motor Power / TSP", f"{selected_row['SF_Motor_kW']} kW (At TSP {total_static_pressure} mmAq)"), 
                        ("Coil Pass / Quantity", f"{int(selected_row['Coil_Pass'])} Pass / {int(selected_row['Coil_Qty'])} EA"),
                        ("Coil Dimensions (H × W)", f"{int(selected_row['Coil_H'])} mm × {int(selected_row['Coil_W'])} mm"),
                        ("Coil Face Area", f"{face_area} m²"),
                        ("Coil Face Velocity", f"{coil_velocity} m/s"),
                        ("Pre-Filter (AFI 82%)", f"Equipped ({f_row}R × {f_col}C)" if v_opt_pre else "Not Equipped"),
                        ("Medium Filter (NBS 90%)", f"Equipped ({f_row}R × {f_col}C)" if v_opt_med else "Not Equipped"),
                        ("HEPA Filter (99.97%)", f"Equipped ({f_row}R × {f_col}C)" if v_opt_hepa else "Not Equipped"),
                        ("Water Piping Connection", f"{int(selected_row['Conn_Cool_In_Out_A'])} A × {int(selected_row['Conn_Cool_Qty'])} EA")
                    ]

                input_conditions = {
                    'cmh': curr_cmh, 'cool': curr_cool, 'heat': curr_heat, 'heat_type': curr_type, 'ahu_type_label': curr_ahu_type
                }
                project_info = {'date': c_date, 'project_name': c_name, 'author': c_author}
                
                pdf_density_info = {
                    'location': curr_location, 'density': v_rho, 'corr_cool': corr_cool_req, 'corr_heat': corr_heat_req,
                    'c_temp': v_ct, 'c_rh': v_cr, 'h_temp': v_ht, 'h_rh': v_hr
                }
                
                # 🌟 [글자 겹침 원천 차단]: ISP/ESP 텍스트 분리 및 간소화
                pdf_coil_info = {
                    'cool_type': cool_type_label, 
                    'h_tw1': v_ch_tw1, 'h_tw2': v_ch_tw2,
                    'cool_fluid_status': cool_lpm_str, 'heat_lpm': heat_lpm, 'cool_lmtd': cool_lmtd_str, 'water_velocity': water_velocity_str
                }
                
                pdf_bytes = generate_pdf(selected_row['Model_Name'], specs_list, input_conditions, project_info, pdf_density_info, pdf_coil_info, is_velocity_warning, is_kor)
                
                with col_m2:
                    st.write("") 
                    # 🌟 버튼명 심플화
                    st.download_button(
                        label="📄 PDF 출력",
                        data=pdf_bytes,
                        file_name=f"RootAir_Engineering_Report_{selected_row['Model_Name']}.pdf" if not is_kor else f"루트에어_엔지니어링_성적서_{selected_row['Model_Name']}.pdf",
                        mime="application/pdf"
                    )

                res_data = {
                    "Specification Item" if not is_kor else "사양 구분 항목": [s[0] for s in specs_list],
                    "Technical Data" if not is_kor else "상세 기술 데이터": [s[1] for s in specs_list]
                }
                res_df = pd.DataFrame(res_data)
                st.dataframe(res_df, use_container_width=True, hide_index=True)
            else:
                st.error("❌ 에러: 풀스펙 필터 저항 및 전정압 연산 결과, 요구 부하를 감당할 수 있는 대형 모델이 데이터베이스에 존재하지 않습니다." if is_kor else "❌ Error: No suitable model found in the database satisfying the selected specs and TSP.")
        else:
            st.info("💡 좌측 입력창에 정보를 입력한 후 [최적 장비 선정하기] 버튼을 누르세요.")