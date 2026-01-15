import streamlit as st
import pymysql

# ---------------------- 全局配置 ----------------------
st.set_page_config(page_title="学生成绩管理系统", layout="wide")

# ---------------------- 数据库连接函数 ----------------------
def connect_db():
    """连接数据库，返回连接对象"""
    try:
        # Sealos云数据库配置（已填好你的信息）
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

# ---------------------- 绩点计算工具函数 ----------------------
def calculate_gpa(score):
    """根据分数计算单门课绩点"""
    score = float(score)
    if score < 60:
        return 0.0
    elif 60 <= score < 70:
        return round(1 + (score - 60) / 10, 1)
    elif 70 <= score < 80:
        return round(2 + (score - 70) / 10, 1)
    elif 80 <= score < 90:
        return round(3 + (score - 80) / 10, 1)
    elif 90 <= score <= 100:
        return round(4 + (score - 90) / 10, 1)
    else:
        return 0.0

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
    
    # 主功能菜单
    menu = st.selectbox(
        "请选择功能",
        ["学生信息查询", "新增学生", "绩点排名", "成绩管理"],
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
                            # 展示表格（修复参数适配问题）
                            st.dataframe(
                                score_data,
                                use_container_width=True
                            )
                            # 显示平均绩点
                            avg_gpa = round(total_gpa / course_count, 2)
                            st.metric("📊 平均绩点", avg_gpa)
                        else:
                            st.info("ℹ️ 该学生暂无选课/成绩记录！")
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
    
    # 3. 绩点排名（所有人可看）
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
                    
                    # 展示排名表格（修复参数适配问题）
                    st.dataframe(
                        rank_data,
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"排名查询失败：{str(e)}")
                finally:
                    cursor.close()
                    db.close()
    
    # 4. 成绩管理（仅管理员可操作）
    if menu == "成绩管理":
        st.subheader("📖 成绩新增/修改")
        if st.session_state["role"] != "admin":
            st.error("❌ 无权限！仅管理员可管理成绩")
            return
        
        # 子菜单：新增/修改成绩
        sub_menu = st.radio("请选择操作", ["新增成绩", "修改成绩"])
        
        # 4.1 新增成绩
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
        
        # 4.2 修改成绩
        if sub_menu == "修改成绩":
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

# ---------------------- 程序入口 ----------------------
if __name__ == "__main__":
    # 初始化session状态
    if "is_login" not in st.session_state:
        st.session_state["is_login"] = False
    
    # 未登录显示登录页，已登录显示主界面
    if not st.session_state["is_login"]:
        login_page()
    else:
        main_page()