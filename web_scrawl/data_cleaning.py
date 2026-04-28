import pandas as pd

cbs_approval = pd.read_excel("web_scrawl/non_ieor_cbs_approval/CBS_electives_CBS.xlsx")
non_ieor_approval = pd.read_excel("web_scrawl/non_ieor_cbs_approval/courses_electives_non_ieor.xlsx")

cbs_info = pd.read_csv("web_scrawl/ cbs_sections.csv", encoding="utf-8-sig")
non_ieor_info = pd.read_csv("web_scrawl/non_ieor_sections.csv", encoding="utf-8-sig")

cbs_df = pd.merge(cbs_info, cbs_approval, left_on="Course Code", right_on="Course Code", how="left")
non_ieor_df = pd.merge(non_ieor_info, non_ieor_approval, left_on="Course Code", right_on="Course Code", how="left")
non_ieor_df.rename(columns={"Course Name_x": "Course Name"}, inplace=True)
ieor_df = pd.read_csv("web_scrawl/IEOR_Spring2026_ieor.csv", encoding="utf-8-sig")

# adjust format
ieor_df["Course Code"] = ieor_df["Section key"].apply(lambda x: x[5:13])
cbs_df["Section"] = cbs_df["Section"].apply(lambda x: '0'*(3-len(str(x))) + str(x))
non_ieor_df["Section"] = non_ieor_df["Section"].apply(lambda x: '0'*(3-len(str(x))) + str(x))
col_lst = ['Section key', 'Course Code', 'Course Name', 'Section', 'Short Name', 'Section URL',
       'Points', 'Day/Time', 'Location', 'Enrollment', 'Notes', 'Instructor',
       'Type', 'Method of Instruction', 'Course Description',
       'Division']
ieor_df = ieor_df[col_lst]
cbs_df = cbs_df[col_lst+['MSOR', 'MSIE', 'MSBA', 'MSE', 'MSFE']]
non_ieor_df = non_ieor_df[col_lst+['MSOR', 'MSIE', 'MSBA', 'MSE', 'MSFE']]

# delete the courses for undergrad & phd
ieor_df["level"] = ieor_df["Course Code"].apply(lambda x: int(x[-4:]))
ieor_df = ieor_df[(ieor_df["level"]>=4000) & (ieor_df["level"]<9000)]
del ieor_df["level"]

ieor_df = ieor_df[~(ieor_df["Course Code"].isin(["IEOR4212","IEOR4307","ORCA2500","IEOR4003"]))]

# delete nan
cbs_df.dropna(subset=["Section key"], inplace=True)
non_ieor_df.dropna(subset=["Section key"], inplace=True)

# split Day/Time and Location
cbs_df["Location"] = cbs_df["Day/Time"].apply(lambda x: " ".join(x.split(" ")[2:]))
cbs_df["Day/Time"] = cbs_df["Day/Time"].apply(lambda x: " ".join(x.split(" ")[:2]))
non_ieor_df["Location"] = non_ieor_df["Day/Time"].apply(lambda x: " ".join(x.split(" ")[2:]))
non_ieor_df["Day/Time"] = non_ieor_df["Day/Time"].apply(lambda x: " ".join(x.split(" ")[:2]))

ieor_df[['MSOR', 'MSIE', 'MSBA', 'MSE', 'MSFE']] = 'elective'
course_info_master = pd.concat([ieor_df, cbs_df, non_ieor_df], ignore_index=True)
# uncapitalize
course_info_master['MSOR'] = course_info_master['MSOR'].str.lower()
course_info_master['MSIE'] = course_info_master['MSIE'].str.lower()
course_info_master['MSBA'] = course_info_master['MSBA'].str.lower()
course_info_master['MSE'] = course_info_master['MSE'].str.lower()
course_info_master['MSFE'] = course_info_master['MSFE'].str.lower()
# if ['MSOR', 'MSIE', 'MSBA', 'MSE', 'MSFE'] == 'no', delete the row
course_info_master = course_info_master[~((course_info_master['MSOR'] == 'no') & 
                                              (course_info_master['MSIE'] == 'no') & 
                                              (course_info_master['MSBA'] == 'no') & 
                                              (course_info_master['MSE'] == 'no') & 
                                              (course_info_master['MSFE'] == 'no'))]

# drop research courses (1-2 1-3 points)
# drop 0 point courses
course_info_master = course_info_master[~course_info_master['Points'].isin(['1-2', '1-3', '0'])]

# Day format
course_info_master["Day"] = course_info_master["Day/Time"].apply(lambda x: list(x.split(" ")[0]))
# mapping dict
day_mapping = {
    'M': 'Monday',
    'T': 'Tuesday',
    'W': 'Wednesday',
    'R': 'Thursday',
    'F': 'Friday',
    'S': 'Saturday',
    'U': 'Sunday'
}
course_info_master["Day"] = course_info_master["Day"].apply(lambda x: [day_mapping.get(d, d) for d in x])
# TIme format
def time_to_decimal(time_str):

    time_str = time_str.strip().lower()
    is_pm = "pm" in time_str
    is_am = "am" in time_str

    time_str = time_str.replace("am", "").replace("pm", "").strip()

    # split
    hour, minute = map(int, time_str.split(":"))

    # 24 hour 
    if is_pm and hour != 12:
        hour += 12
    if is_am and hour == 12:
        hour = 0

    return hour + minute / 60

course_info_master["Time_start"] = course_info_master["Day/Time"].apply(lambda x: time_to_decimal(x.split(" ")[1].split("-")[0]))
course_info_master["Time_end"] = course_info_master["Day/Time"].apply(lambda x: time_to_decimal(x.split(" ")[1].split("-")[1]))

del course_info_master["Day/Time"]
del course_info_master["Section URL"]

course_info_master.to_csv("web_scrawl/Spring2026_course_info_master.csv", index=False, encoding="utf-8-sig")