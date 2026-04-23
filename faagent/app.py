import streamlit as st
from agent.log_parser import parse_test_log
from agent.repair_learner import load_repair_excel
from agent.fa_reasoner import generate_fa
from report.ppt_generator import generate_ppt

st.set_page_config(page_title="FA AI Agent", layout="wide")

st.title("🔧 FA AI Agent – Test Log 分析 & 报告生成")

log_file = st.file_uploader("📂 上传测试 JSON Log", type=["json"])
repair_file = st.file_uploader("📊 上传维修 Excel 报表", type=["xlsx"])

if st.button("🚀 生成 FA 报告"):
    if not log_file or not repair_file:
        st.warning("请先上传测试 Log 和维修 Excel")
    else:
        log_info = parse_test_log(log_file)
        repair_db = load_repair_excel(repair_file)

        fa_result = generate_fa(log_info, repair_db)
        ppt_path = generate_ppt(log_info, fa_result)

        st.success("FA 报告已生成")
        st.download_button("📥 下载 FA PPT", open(ppt_path, "rb"), file_name="FA_Report.pptx")