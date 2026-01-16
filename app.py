import streamlit as st
import pymysql
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO, StringIO
from PIL import Image

# ---------------------- 全局配置 ----------------------
st.set_page_config(page_title="学生成绩管理系统", layout="wide")

# 设置matplotlib中文显示
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams['axes.unicode_minus'] = False

# ---------------------- 数据库连接函数 ----------------------
def connect_db():
    """连接数据库，返回连接对象"""
    try:
        # Sealos云数据库配置
        conn = pymysql.connect(
            host="dbconn.sealoshzh.site",  
            port=40210,         
            user="root",       
            password="d7f6x5pf",
            db="grade_management",
            charset="utf8mb4"
        )
        return conn
    except Exception as e:
        st.error(f"数据库连接失败：{str(e)}")
        st.warning("请检查：1. 云数据库是否正常运行 2. 账号密码/端口是否正确")
        return None

# ---------------------- 工具函数 ----------------------
def calculate_gpa(score):
    """根据分数计算单门课绩点"""
    score = float(score)
    if score < 60:
        return 0.0
    score -= 60
    return min(1 + score/10, 4.0) if score < 30 else 4 + (score-30)/10

def validate_score(score):
    """验证成绩是否合法"""
    try:
        score = float(score)
        if 0 <= score <= 100:
            return score, True
        else:
            st.warning("成绩必须在0-100之间！")
            return None, False
    except ValueError:
        st.warning("成绩必须是数字！")
        return None, False

# ---------------------- 导出功能函数 ----------------------
def export_to_excel(data, filename="学生信息"):
    """导出数据到Excel"""
    output = BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='学生信息')
    output.seek(0)
    return output

def export_to_csv(data, filename="学生信息"):
    """导出数据到CSV（备用方案）"""
    output = StringIO()
    df = pd.DataFrame(data)
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    return output

def generate_score_chart(class_name, course_id, course_name, scores):
    """生成成绩统计图表"""
    # 统计成绩分布
    grade_levels = {"不及格": 0, "及格": 0, "良好": 0, "优秀": 0}
    total_scores = 0
    score_count = 0
    
    for score in scores:
        if score is not None:
            score = float(score)
            total_scores += score
            score_count += 1
            
            if score < 60:
                grade_levels["不及格"] += 1
            elif 60 <= score < 80:
                grade_levels["及格"] += 1
            elif 80 <= score < 90:
                grade_levels["良好"] += 1
            elif 90 <= score <= 100:
                grade_levels["优秀"] += 1
    
    # 计算统计指标
    avg_score = round(total_scores / score_count, 2) if score_count > 0 else 0.0
    total = sum(grade_levels.values())
    grade_percentages = {k: round(v/total*100, 1) for k, v in grade_levels.items()}
    
    # 生成图表
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    labels = list(grade_levels.keys())
    sizes = list(grade_levels.values())
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    explode = (0.05, 0, 0, 0)
    
    # 饼状图
    wedges, texts, autotexts = ax1.pie(
        sizes, 
        explode=explode,
        labels=labels,
        colors=colors,
        autopct='%1.1f%%',
        shadow=True,
        startangle=90
    )
    ax1.set_title(f'{class_name}班-{course_name}（{course_id}）成绩等级分布\n(参考人数：{score_count}，平均分：{avg_score})', fontsize=12)
    
    # 柱状图
    ax2.bar(labels, sizes, color=colors)
    ax2.set_title(f'{class_name}班-{course_name}（{course_id}）各成绩等级人数', fontsize=12)
    ax2.set_ylabel('学生人数')
    for i, v in enumerate(sizes):
        ax2.text(i, v + 0.1, str(v), ha='center', va='bottom')
    
    plt.tight_layout()
    
    # 保存图表到BytesIO
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)
    img = Image.open(img_buffer)
    
    # 返回图表和统计信息
    return img, {
        "class_name": class_name,
        "course_name": course_name,
        "course_id": course_id,
        "student_count": score_count,
        "avg_score": avg_score,
        "grade_distribution": grade_levels,
        "grade_percentages": grade_percentages
    }

# ---------------------- 登录页面 ----------------------
def login_page():
    st.title("📚 学生成绩管理系统 - 登录")
    st.divider()
    
    # 登录表单
    with st.form("login_form"):
        username = st.text_input("账号", placeholder="请输入登录账号")
        password = st.text_input("密码", type="password", placeholder="请输入登录密码")
        submit_btn = st.form_submit_button("登录", type="primary")
        
        if submit_btn:
            if not (username and password):
                st.warning("⚠️ 账号和密码不能为空！")
                return
            
            # 连接数据库验证账号密码
            db = connect_db()
            if db:
                cursor = db.cursor()
                try:
                    # 查询用户信息
                    cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
                    user = cursor.fetchone()
                    if user:
                        # 验证密码（明文，适配测试场景）
                        if user[2] == password:
                            # 登录成功，保存用户状态
                            st.session_state["is_login"] = True
                            st.session_state["username"] = username
                            st.session_state["role"] = user[3]  # admin/teacher
                            st.success("✅ 登录成功！正在跳转...")
                            st.rerun()  # 刷新页面跳主界面
                        else:
                            st.error("❌ 密码错误！")
                    else:
                        st.error("❌ 账号不存在！")
                except Exception as e:
                    st.error(f"登录失败：{str(e)}")
                finally:
                    cursor.close()
                    db.close()

# ---------------------- 主功能页面 ----------------------
def main_page():
    # 侧边栏：用户信息 + 退出登录
    with st.sidebar:
        st.header(f"当前登录：{st.session_state['username']}")
        st.caption(f"角色：{st.session_state['role']}")
        if st.button("退出登录", type="secondary"):
            st.session_state.clear()
            st.rerun()
        st.divider()
    
    # 主功能菜单（完整功能）
    menu = st.selectbox(
        "请选择功能",
        [
            "学生信息查询", "新增学生", "修改学生信息", "删除学生",
            "课程管理", "成绩管理", "绩点排名", "班级+学科成绩统计"
        ],
        index=0
    )
    
    # 1. 学生信息查询（所有人可看）
    if menu == "学生信息查询":
        st.subheader("🔍 学生信息+成绩+绩点查询")
        with st.form("query_form"):
            stu_id = st.text_input("请输入学生学号", placeholder="例如：2024001")
            query_btn = st.form_submit_button("查询")
            
            if query_btn:
                if not stu_id:
                    st.warning("⚠️ 请输入学号！")
                    return
                
                db = connect_db()
                if db:
                    cursor = db.cursor()
                    try:
                        # 查学生基础信息
                        cursor.execute("SELECT * FROM student WHERE student_id = %s", (stu_id,))
                        stu_info = cursor.fetchone()
                        if not stu_info:
                            st.info("ℹ️ 未查询到该学生信息！")
                            return
                        
                        # 展示基础信息
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("学号", stu_info[0])
                        col2.metric("姓名", stu_info[1])
                        col3.metric("性别", stu_info[2])
                        col4.metric("班级", stu_info[3])
                        st.divider()
                        
                        # 查该学生成绩
                        cursor.execute("""
                            SELECT c.course_name, sc.score 
                            FROM score sc
                            JOIN course c ON sc.course_id = c.course_id
                            WHERE sc.student_id = %s
                        """, (stu_id,))
                        scores = cursor.fetchall()
                        
                        # 整理导出数据
                        export_data = []
                        # 基础信息行
                        export_data.append({
                            "学号": stu_info[0],
                            "姓名": stu_info[1],
                            "性别": stu_info[2],
                            "班级": stu_info[3],
                            "课程名称": "——",
                            "成绩": "——",
                            "绩点": "——"
                        })
                        
                        if scores:
                            st.subheader("📝 成绩与绩点")
                            total_gpa = 0.0
                            course_count = len(scores)
                            # 整理成绩数据
                            score_data = []
                            for course, score in scores:
                                gpa = calculate_gpa(score)
                                total_gpa += gpa
                                score_data.append({
                                    "课程名称": course,
                                    "成绩": score,
                                    "单门绩点": gpa
                                })
                                export_data.append({
                                    "学号": stu_info[0],
                                    "姓名": "",
                                    "性别": "",
                                    "班级": "",
                                    "课程名称": course,
                                    "成绩": score,
                                    "绩点": round(gpa, 1)
                                })
                            # 展示表格
                            st.dataframe(score_data, use_container_width=True)
                            # 显示平均绩点
                            avg_gpa = round(total_gpa / course_count, 2)
                            st.metric("📊 平均绩点", avg_gpa)
                            # 添加平均绩点到导出数据
                            export_data.append({
                                "学号": stu_info[0],
                                "姓名": "",
                                "性别": "",
                                "班级": "",
                                "课程名称": "平均绩点",
                                "成绩": "——",
                                "绩点": avg_gpa
                            })
                        else:
                            st.info("ℹ️ 该学生暂无选课/成绩记录！")
                            export_data.append({
                                "学号": stu_info[0],
                                "姓名": "",
                                "性别": "",
                                "班级": "",
                                "课程名称": "无选课记录",
                                "成绩": "无成绩",
                                "绩点": 0.0
                            })
                        
                        # 导出功能
                        st.divider()
                        col_export1, col_export2 = st.columns(2)
                        with col_export1:
                            # 导出Excel
                            excel_data = export_to_excel(export_data, f"学生{stu_id}信息")
                            st.download_button(
                                label="📥 导出Excel文件",
                                data=excel_data,
                                file_name=f"学生{stu_id}信息.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        with col_export2:
                            # 导出CSV（兼容更多设备）
                            csv_data = export_to_csv(export_data, f"学生{stu_id}信息")
                            st.download_button(
                                label="📥 导出CSV文件",
                                data=csv_data,
                                file_name=f"学生{stu_id}信息.csv",
                                mime="text/csv"
                            )
                            
                    except Exception as e:
                        st.error(f"查询失败：{str(e)}")
                    finally:
                        cursor.close()
                        db.close()
    
    # 2. 新增学生（仅管理员可操作）
    if menu == "新增学生":
        st.subheader("➕ 新增学生")
        # 权限判断
        if st.session_state["role"] != "admin":
            st.error("❌ 无权限！仅管理员可新增学生")
            return
        
        with st.form("add_stu_form"):
            col1, col2 = st.columns(2)
            stu_id = col1.text_input("学号", placeholder="唯一，例如：2024001")
            stu_name = col2.text_input("姓名", placeholder="例如：张三")
            stu_gender = col1.selectbox("性别", ["男", "女"])
            stu_class = col2.text_input("班级", placeholder="例如：计科2401")
            add_btn = st.form_submit_button("提交新增", type="primary")
            
            if add_btn:
                if not (stu_id and stu_name and stu_gender and stu_class):
                    st.warning("⚠️ 所有字段不能为空！")
                    return
                
                db = connect_db()
                if db:
                    cursor = db.cursor()
                    try:
                        # 检查学号是否已存在
                        cursor.execute("SELECT * FROM student WHERE student_id = %s", (stu_id,))
                        if cursor.fetchone():
                            st.error("❌ 学号已存在！")
                            return
                        # 新增学生
                        cursor.execute(
                            "INSERT INTO student (student_id, name, gender, class) VALUES (%s, %s, %s, %s)",
                            (stu_id, stu_name, stu_gender, stu_class)
                        )
                        db.commit()
                        st.success("✅ 学生新增成功！")
                        # 刷新表单
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"新增失败：{str(e)}")
                    finally:
                        cursor.close()
                        db.close()
    
    # 3. 修改学生信息（仅管理员可操作）
    if menu == "修改学生信息":
        st.subheader("✏️ 修改学生信息")
        # 权限判断
        if st.session_state["role"] != "admin":
            st.error("❌ 无权限！仅管理员可修改学生信息")
            return
        
        # 选择修改类型
        update_type = st.radio("修改类型", ["基础信息", "成绩"])
        
        with st.form("update_stu_form"):
            stu_id = st.text_input("学生学号", placeholder="例如：2024001")
            
            if update_type == "基础信息":
                col1, col2 = st.columns(2)
                new_name = col1.text_input("新姓名", placeholder="例如：张三")
                new_gender = col2.selectbox("新性别", ["男", "女"])
                new_class = col1.text_input("新班级", placeholder="例如：计科2401")
            else:
                col1, col2 = st.columns(2)
                course_id = col1.text_input("课程ID", placeholder="例如：C001")
                new_score = col2.number_input("新成绩", min_value=0.0, max_value=100.0, step=0.5)
            
            update_btn = st.form_submit_button("提交修改", type="primary")
            
            if update_btn:
                if not stu_id:
                    st.warning("⚠️ 请输入学生学号！")
                    return
                
                db = connect_db()
                if db:
                    cursor = db.cursor()
                    try:
                        # 检查学生是否存在
                        cursor.execute("SELECT * FROM student WHERE student_id = %s", (stu_id,))
                        if not cursor.fetchone():
                            st.error("❌ 学生不存在！")
                            return
                        
                        if update_type == "基础信息":
                            if not (new_name and new_gender and new_class):
                                st.warning("⚠️ 所有基础信息字段不能为空！")
                                return
                            # 修改基础信息
                            cursor.execute(
                                "UPDATE student SET name = %s, gender = %s, class = %s WHERE student_id = %s",
                                (new_name, new_gender, new_class, stu_id)
                            )
                        else:
                            if not course_id:
                                st.warning("⚠️ 课程ID不能为空！")
                                return
                            # 验证成绩
                            score_valid, is_ok = validate_score(new_score)
                            if not is_ok:
                                return
                            # 检查课程是否存在
                            cursor.execute("SELECT * FROM course WHERE course_id = %s", (course_id,))
                            if not cursor.fetchone():
                                st.error("❌ 课程不存在！")
                                return
                            # 检查成绩记录是否存在
                            cursor.execute("SELECT * FROM score WHERE student_id = %s AND course_id = %s", (stu_id, course_id))
                            if not cursor.fetchone():
                                st.error("❌ 该学生未选此课程，无成绩可修改！")
                                return
                            # 修改成绩
                            cursor.execute(
                                "UPDATE score SET score = %s WHERE student_id = %s AND course_id = %s",
                                (new_score, stu_id, course_id)
                            )
                        
                        db.commit()
                        if cursor.rowcount > 0:
                            st.success("✅ 信息修改成功！")
                        else:
                            st.info("ℹ️ 无数据被修改！")
                    except Exception as e:
                        db.rollback()
                        st.error(f"修改失败：{str(e)}")
                    finally:
                        cursor.close()
                        db.close()
    
    # 4. 删除学生（仅管理员可操作）
    if menu == "删除学生":
        st.subheader("🗑️ 删除学生")
        # 权限判断
        if st.session_state["role"] != "admin":
            st.error("❌ 无权限！仅管理员可删除学生")
            return
        
        with st.form("delete_stu_form"):
            stu_id = st.text_input("请输入要删除的学生学号", placeholder="例如：2024001")
            # 二次确认（防止误删）
            confirm_delete = st.checkbox("我确认要删除该学生（会同步删除其成绩）")
            delete_btn = st.form_submit_button("删除学生", type="primary")
            
            if delete_btn:
                if not stu_id:
                    st.warning("⚠️ 请输入要删除的学生学号！")
                    return
                if not confirm_delete:
                    st.warning("⚠️ 请勾选确认删除！")
                    return
                
                db = connect_db()
                if db:
                    cursor = db.cursor()
                    try:
                        # 检查学生是否存在
                        cursor.execute("SELECT * FROM student WHERE student_id = %s", (stu_id,))
                        if not cursor.fetchone():
                            st.error("❌ 该学生不存在！")
                            return
                        
                        # 先删除该学生的成绩（外键关联）
                        cursor.execute("DELETE FROM score WHERE student_id = %s", (stu_id,))
                        # 再删除学生信息
                        cursor.execute("DELETE FROM student WHERE student_id = %s", (stu_id,))
                        db.commit()
                        
                        if cursor.rowcount > 0:
                            st.success("✅ 学生删除成功（含关联成绩）！")
                        else:
                            st.info("ℹ️ 无学生数据被删除！")
                        # 刷新表单
                        st.rerun()
                    except Exception as e:
                        db.rollback()
                        st.error(f"删除失败：{str(e)}")
                    finally:
                        cursor.close()
                        db.close()
    
    # 5. 课程管理（仅管理员可操作）
    if menu == "课程管理":
        st.subheader("📚 课程管理")
        # 权限判断
        if st.session_state["role"] != "admin":
            st.error("❌ 无权限！仅管理员可管理课程")
            return
        
        # 课程管理子菜单
        course_submenu = st.radio("课程操作", ["新增课程", "修改课程", "删除课程"])
        
        # 5.1 新增课程
        if course_submenu == "新增课程":
            with st.form("add_course_form"):
                col1, col2, col3 = st.columns(3)
                course_id = col1.text_input("课程ID", placeholder="例如：C001")
                course_name = col2.text_input("课程名称", placeholder="例如：Python程序设计")
                credit = col3.number_input("学分", min_value=1, max_value=10, step=1)
                add_course_btn = st.form_submit_button("新增课程", type="primary")
                
                if add_course_btn:
                    if not (course_id and course_name):
                        st.warning("⚠️ 课程ID和名称不能为空！")
                        return
                    
                    db = connect_db()
                    if db:
                        cursor = db.cursor()
                        try:
                            # 检查课程ID是否已存在
                            cursor.execute("SELECT * FROM course WHERE course_id = %s", (course_id,))
                            if cursor.fetchone():
                                st.error("❌ 课程ID已存在！")
                                return
                            # 新增课程
                            cursor.execute(
                                "INSERT INTO course (course_id, course_name, credit) VALUES (%s, %s, %s)",
                                (course_id, course_name, credit)
                            )
                            db.commit()
                            st.success("✅ 课程新增成功！")
                        except Exception as e:
                            db.rollback()
                            st.error(f"新增失败：{str(e)}")
                        finally:
                            cursor.close()
                            db.close()
        
        # 5.2 修改课程
        elif course_submenu == "修改课程":
            with st.form("update_course_form"):
                col1, col2, col3 = st.columns(3)
                course_id = col1.text_input("课程ID", placeholder="例如：C001")
                new_course_name = col2.text_input("新课程名称", placeholder="例如：Python程序设计")
                new_credit = col3.number_input("新学分", min_value=1, max_value=10, step=1)
                update_course_btn = st.form_submit_button("修改课程", type="primary")
                
                if update_course_btn:
                    if not (course_id and new_course_name):
                        st.warning("⚠️ 课程ID和新名称不能为空！")
                        return
                    
                    db = connect_db()
                    if db:
                        cursor = db.cursor()
                        try:
                            # 检查课程是否存在
                            cursor.execute("SELECT * FROM course WHERE course_id = %s", (course_id,))
                            if not cursor.fetchone():
                                st.error("❌ 课程不存在！")
                                return
                            # 修改课程
                            cursor.execute(
                                "UPDATE course SET course_name = %s, credit = %s WHERE course_id = %s",
                                (new_course_name, new_credit, course_id)
                            )
                            db.commit()
                            if cursor.rowcount > 0:
                                st.success("✅ 课程修改成功！")
                            else:
                                st.info("ℹ️ 无数据被修改！")
                        except Exception as e:
                            db.rollback()
                            st.error(f"修改失败：{str(e)}")
                        finally:
                            cursor.close()
                            db.close()
        
        # 5.3 删除课程
        elif course_submenu == "删除课程":
            with st.form("delete_course_form"):
                course_id = st.text_input("课程ID", placeholder="例如：C001")
                confirm_delete = st.checkbox("我确认要删除该课程")
                delete_course_btn = st.form_submit_button("删除课程", type="primary")
                
                if delete_course_btn:
                    if not course_id:
                        st.warning("⚠️ 请输入课程ID！")
                        return
                    if not confirm_delete:
                        st.warning("⚠️ 请勾选确认删除！")
                        return
                    
                    db = connect_db()
                    if db:
                        cursor = db.cursor()
                        try:
                            # 检查课程是否存在
                            cursor.execute("SELECT * FROM course WHERE course_id = %s", (course_id,))
                            if not cursor.fetchone():
                                st.error("❌ 课程不存在！")
                                return
                            # 删除课程
                            cursor.execute("DELETE FROM course WHERE course_id = %s", (course_id,))
                            db.commit()
                            if cursor.rowcount > 0:
                                st.success("✅ 课程删除成功！")
                            else:
                                st.info("ℹ️ 无课程数据被删除！")
                        except Exception as e:
                            db.rollback()
                            st.error(f"删除失败：{str(e)}")
                        finally:
                            cursor.close()
                            db.close()
    
    # 6. 成绩管理（仅管理员可操作）
    if menu == "成绩管理":
        st.subheader("📖 成绩管理")
        if st.session_state["role"] != "admin":
            st.error("❌ 无权限！仅管理员可管理成绩")
            return
        
        # 子菜单：新增/修改/删除成绩
        sub_menu = st.radio("请选择操作", ["新增成绩", "修改成绩", "删除成绩"])
        
        # 6.1 新增成绩
        if sub_menu == "新增成绩":
            with st.form("add_score_form"):
                col1, col2, col3 = st.columns(3)
                stu_id = col1.text_input("学生学号")
                course_id = col2.text_input("课程ID")
                score = col3.number_input("成绩", min_value=0.0, max_value=100.0, step=0.5)
                add_score_btn = st.form_submit_button("新增成绩", type="primary")
                
                if add_score_btn:
                    if not (stu_id and course_id):
                        st.warning("⚠️ 学号和课程ID不能为空！")
                        return
                    
                    db = connect_db()
                    if db:
                        cursor = db.cursor()
                        try:
                            # 检查学生和课程是否存在
                            cursor.execute("SELECT * FROM student WHERE student_id = %s", (stu_id,))
                            if not cursor.fetchone():
                                st.error("❌ 学生不存在！")
                                return
                            cursor.execute("SELECT * FROM course WHERE course_id = %s", (course_id,))
                            if not cursor.fetchone():
                                st.error("❌ 课程不存在！")
                                return
                            # 检查是否已存在该成绩
                            cursor.execute("SELECT * FROM score WHERE student_id = %s AND course_id = %s", (stu_id, course_id))
                            if cursor.fetchone():
                                st.error("❌ 该学生已存在该课程成绩！")
                                return
                            # 新增成绩
                            cursor.execute(
                                "INSERT INTO score (student_id, course_id, score) VALUES (%s, %s, %s)",
                                (stu_id, course_id, score)
                            )
                            db.commit()
                            st.success("✅ 成绩新增成功！")
                        except Exception as e:
                            db.rollback()
                            st.error(f"新增失败：{str(e)}")
                        finally:
                            cursor.close()
                            db.close()
        
        # 6.2 修改成绩
        elif sub_menu == "修改成绩":
            with st.form("update_score_form"):
                col1, col2, col3 = st.columns(3)
                stu_id = col1.text_input("学生学号")
                course_id = col2.text_input("课程ID")
                new_score = col3.number_input("新成绩", min_value=0.0, max_value=100.0, step=0.5)
                update_score_btn = st.form_submit_button("修改成绩", type="primary")
                
                if update_score_btn:
                    if not (stu_id and course_id):
                        st.warning("⚠️ 学号和课程ID不能为空！")
                        return
                    
                    db = connect_db()
                    if db:
                        cursor = db.cursor()
                        try:
                            # 检查成绩是否存在
                            cursor.execute("SELECT * FROM score WHERE student_id = %s AND course_id = %s", (stu_id, course_id))
                            if not cursor.fetchone():
                                st.error("❌ 该成绩不存在！")
                                return
                            # 修改成绩
                            cursor.execute(
                                "UPDATE score SET score = %s WHERE student_id = %s AND course_id = %s",
                                (new_score, stu_id, course_id)
                            )
                            db.commit()
                            if cursor.rowcount > 0:
                                st.success("✅ 成绩修改成功！")
                            else:
                                st.info("ℹ️ 无数据被修改！")
                        except Exception as e:
                            db.rollback()
                            st.error(f"修改失败：{str(e)}")
                        finally:
                            cursor.close()
                            db.close()
        
        # 6.3 删除成绩
        elif sub_menu == "删除成绩":
            with st.form("delete_score_form"):
                col1, col2 = st.columns(2)
                stu_id = col1.text_input("学生学号")
                course_id = col2.text_input("课程ID")
                confirm_delete = st.checkbox("我确认要删除该成绩")
                delete_score_btn = st.form_submit_button("删除成绩", type="primary")
                
                if delete_score_btn:
                    if not (stu_id and course_id):
                        st.warning("⚠️ 学号和课程ID不能为空！")
                        return
                    if not confirm_delete:
                        st.warning("⚠️ 请勾选确认删除！")
                        return
                    
                    db = connect_db()
                    if db:
                        cursor = db.cursor()
                        try:
                            # 检查成绩是否存在
                            cursor.execute("SELECT * FROM score WHERE student_id = %s AND course_id = %s", (stu_id, course_id))
                            if not cursor.fetchone():
                                st.error("❌ 该成绩不存在！")
                                return
                            # 删除成绩
                            cursor.execute("DELETE FROM score WHERE student_id = %s AND course_id = %s", (stu_id, course_id))
                            db.commit()
                            if cursor.rowcount > 0:
                                st.success("✅ 成绩删除成功！")
                            else:
                                st.info("ℹ️ 无成绩数据被删除！")
                        except Exception as e:
                            db.rollback()
                            st.error(f"删除失败：{str(e)}")
                        finally:
                            cursor.close()
                            db.close()
    
    # 7. 绩点排名（所有人可看）
    if menu == "绩点排名":
        st.subheader("🏆 学生绩点排名（降序）")
        query_rank_btn = st.button("刷新排名", type="primary")
        
        if query_rank_btn:
            db = connect_db()
            if db:
                cursor = db.cursor()
                try:
                    # 查所有学生
                    cursor.execute("SELECT student_id, name, class FROM student")
                    all_students = cursor.fetchall()
                    if not all_students:
                        st.info("ℹ️ 暂无学生数据！")
                        return
                    
                    # 计算每个学生的平均绩点
                    rank_data = []
                    export_rank_data = []
                    for stu in all_students:
                        stu_id, stu_name, stu_class = stu
                        # 查该学生成绩
                        cursor.execute("SELECT score FROM score WHERE student_id = %s", (stu_id,))
                        scores = cursor.fetchall()
                        
                        total_gpa = 0.0
                        course_count = 0
                        for score in scores:
                            if score[0] is not None:
                                total_gpa += calculate_gpa(score[0])
                                course_count += 1
                        avg_gpa = round(total_gpa / course_count, 2) if course_count > 0 else 0.0
                        rank_data.append({
                            "排名": "",  # 占位，后续填充
                            "学号": stu_id,
                            "姓名": stu_name,
                            "班级": stu_class,
                            "平均绩点": avg_gpa
                        })
                    
                    # 按平均绩点降序排序
                    rank_data.sort(key=lambda x: x["平均绩点"], reverse=True)
                    # 填充排名
                    for i in range(len(rank_data)):
                        rank_data[i]["排名"] = i + 1
                        export_rank_data.append({
                            "排名": i + 1,
                            "学号": rank_data[i]["学号"],
                            "姓名": rank_data[i]["姓名"],
                            "班级": rank_data[i]["班级"],
                            "平均绩点": rank_data[i]["平均绩点"]
                        })
                    
                    # 展示排名表格
                    st.dataframe(rank_data, use_container_width=True)
                    
                    # 导出排名数据
                    st.divider()
                    col1, col2 = st.columns(2)
                    with col1:
                        # 导出Excel
                        excel_data = export_to_excel(export_rank_data, "学生绩点排名")
                        st.download_button(
                            label="📥 导出排名为Excel",
                            data=excel_data,
                            file_name="学生绩点排名.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    with col2:
                        # 导出CSV
                        csv_data = export_to_csv(export_rank_data, "学生绩点排名")
                        st.download_button(
                            label="📥 导出排名为CSV",
                            data=csv_data,
                            file_name="学生绩点排名.csv",
                            mime="text/csv"
                        )
                        
                except Exception as e:
                    st.error(f"排名查询失败：{str(e)}")
                finally:
                    cursor.close()
                    db.close()
    
    # 8. 班级+学科成绩统计
    if menu == "班级+学科成绩统计":
        st.subheader("📊 班级+学科成绩统计与可视化")
        
        with st.form("class_course_analysis_form"):
            col1, col2 = st.columns(2)
            class_name = col1.text_input("班级名称", placeholder="例如：计科2401")
            course_id = col2.text_input("课程ID", placeholder="例如：C001")
            analyze_btn = st.form_submit_button("统计并生成图表", type="primary")
            
            if analyze_btn:
                if not (class_name and course_id):
                    st.warning("⚠️ 班级名称和课程ID不能为空！")
                    return
                
                db = connect_db()
                if db:
                    cursor = db.cursor()
                    try:
                        # 查询课程名称
                        cursor.execute("SELECT course_name FROM course WHERE course_id = %s", (course_id,))
                        course_name = cursor.fetchone()
                        if not course_name:
                            st.error("❌ 课程ID不存在！")
                            return
                        course_name = course_name[0]
                        
                        # 查询该班级选了这门课的学生成绩
                        cursor.execute("""
                            SELECT sc.score 
                            FROM student s
                            JOIN score sc ON s.student_id = sc.student_id
                            WHERE s.class = %s AND sc.course_id = %s
                        """, (class_name, course_id))
                        scores = cursor.fetchall()
                        scores = [score[0] for score in scores if score[0] is not None]
                        
                        if not scores:
                            st.info(f"ℹ️ {class_name}班暂无{course_name}（{course_id}）的成绩数据！")
                            return
                        
                        # 生成图表和统计信息
                        img, stats = generate_score_chart(class_name, course_id, course_name, scores)
                        
                        # 展示统计信息
                        st.subheader("📈 统计结果")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("参与统计人数", stats["student_count"])
                            st.metric("学科平均分", stats["avg_score"])
                        with col2:
                            st.write("### 成绩等级分布")
                            for level, count in stats["grade_distribution"].items():
                                percentage = stats["grade_percentages"][level]
                                st.write(f"- {level}：{count}人 ({percentage}%)")
                        
                        # 展示图表
                        st.subheader("📊 成绩可视化图表")
                        st.image(img, use_column_width=True)
                        
                        # 导出图表
                        img_buffer = BytesIO()
                        img.save(img_buffer, format='PNG')
                        img_buffer.seek(0)
                        st.download_button(
                            label="📥 下载成绩图表",
                            data=img_buffer,
                            file_name=f"{class_name}班{course_name}成绩统计.png",
                            mime="image/png"
                        )
                        
                        # 导出统计数据
                        stats_data = [
                            {"指标": "班级", "值": stats["class_name"]},
                            {"指标": "课程ID", "值": stats["course_id"]},
                            {"指标": "课程名称", "值": stats["course_name"]},
                            {"指标": "参与统计人数", "值": stats["student_count"]},
                            {"指标": "学科平均分", "值": stats["avg_score"]},
                            {"指标": "不及格人数", "值": f"{stats['grade_distribution']['不及格']}人 ({stats['grade_percentages']['不及格']}%)"},
                            {"指标": "及格人数", "值": f"{stats['grade_distribution']['及格']}人 ({stats['grade_percentages']['及格']}%)"},
                            {"指标": "良好人数", "值": f"{stats['grade_distribution']['良好']}人 ({stats['grade_percentages']['良好']}%)"},
                            {"指标": "优秀人数", "值": f"{stats['grade_distribution']['优秀']}人 ({stats['grade_percentages']['优秀']}%)"},
                        ]
                        excel_data = export_to_excel(stats_data, f"{class_name}班{course_name}成绩统计")
                        st.download_button(
                            label="📥 下载统计数据Excel",
                            data=excel_data,
                            file_name=f"{class_name}班{course_name}成绩统计.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                    except Exception as e:
                        st.error(f"统计失败：{str(e)}")
                    finally:
                        cursor.close()
                        db.close()

# ---------------------- 程序入口 ----------------------
if __name__ == "__main__":
    # 初始化session状态
    if "is_login" not in st.session_state:
        st.session_state["is_login"] = False
    
    # 安装依赖提示（首次运行）
    if st.session_state.get("show_install_hint", True):
        with st.expander("📝 首次运行请先安装依赖", expanded=False):
            st.code("pip install pandas openpyxl matplotlib pillow", language="bash")
        st.session_state["show_install_hint"] = False
    
    # 未登录显示登录页，已登录显示主界面
    if not st.session_state["is_login"]:
        login_page()
    else:
        main_page()