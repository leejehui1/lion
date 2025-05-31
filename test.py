from flask import Flask, render_template_string, request, redirect, session
from supabase import create_client
import requests
import uuid
from datetime import datetime, timedelta

# Supabase 설정
SUPABASE_URL = 'https://trarzmynnaphzloclzvi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRyYXJ6bXlubmFwaHpsb2NsenZpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ3MjYzOTAsImV4cCI6MjA2MDMwMjM5MH0.bgYYKe9Su4aUykxFqM96WDAb3jrDz3XM-I8C6zPffwE'

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = "your-secret-key"

# 유틸 함수
def safe_date(val): return val if val else None
def safe_int(val): 
    try: return int(val)
    except: return 0
def safe_bool(val): return val == 'on'

# 구글 id_token 검증 함수
def verify_google_token(id_token):
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
    res = requests.get(url)
    if res.status_code != 200:
        return None
    data = res.json()
    if "sub" in data and "email" in data and "name" in data:
        return {
            "sub": data["sub"],
            "email": data["email"],
            "name": data["name"]
        }
    return None

# === 사용자 인증 함수 ===
def registerUser(data):
    try:
        # 이미 존재하는 이메일인지 확인
        existing_user = supabase.table("user").select("*").eq("email", data["email"]).execute()
        if existing_user.data:
            return {"error": "이미 존재하는 이메일입니다."}
        
        # 새 사용자 등록
        user_id = str(uuid.uuid4())
        new_user = {
            "id": user_id,
            "email": data["email"],
            "password": data["password"],  # 실제 구현시 반드시 암호화 필요
            "name": data.get("name", ""),
            "created_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table("user").insert(new_user).execute()
        if result.data:
            return {"success": True, "user": result.data[0]}
        return {"error": "사용자 등록 실패"}
    except Exception as e:
        return {"error": str(e)}

def loginUser(email, password):
    try:
        # 이메일로 사용자 찾기
        result = supabase.table("user").select("*").eq("email", email).execute()
        if not result.data:
            return {"error": "사용자를 찾을 수 없습니다."}
        
        user = result.data[0]
        # 비밀번호 확인 (실제 구현시 암호화된 비밀번호 비교 필요)
        if user["password"] != password:
            return {"error": "잘못된 비밀번호입니다."}
        
        # 세션에 사용자 정보 저장
        session['user'] = {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"]
        }
        return {"success": True, "user": session['user']}
    except Exception as e:
        return {"error": str(e)}

def logoutUser():
    try:
        session.clear()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

def getUserById(id):
    try:
        result = supabase.table("user").select("*").eq("id", id).execute()
        if not result.data:
            return {"error": "사용자를 찾을 수 없습니다."}
        
        user = result.data[0]
        # 비밀번호는 제외하고 반환
        del user["password"]
        return {"success": True, "user": user}
    except Exception as e:
        return {"error": str(e)}

def loginByToken(token):
    try:
        # JWT 토큰 검증 (실제 구현시 proper JWT 검증 필요)
        user_info = verify_google_token(token)  # 기존 함수 재사용
        if not user_info:
            return {"error": "유효하지 않은 토큰입니다."}
        
        # 사용자 정보 조회 또는 생성
        result = supabase.table("user").select("*").eq("email", user_info["email"]).execute()
        if result.data:
            user = result.data[0]
        else:
            # 새 사용자 생성
            new_user = {
                "id": str(uuid.uuid4()),
                "email": user_info["email"],
                "name": user_info["name"],
                "created_at": datetime.utcnow().isoformat()
            }
            result = supabase.table("user").insert(new_user).execute()
            user = result.data[0]
        
        # 세션에 사용자 정보 저장
        session['user'] = {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"]
        }
        return {"success": True, "user": session['user']}
    except Exception as e:
        return {"error": str(e)}

# === 스케줄 관리 함수 ===
"""
팀 스케줄 관리 함수들의 사용 예시:

1. 월간 스케줄 조회
response = requests.get('http://localhost:5000/api/schedule/month/팀ID/스케줄ID/2025-04')

2. 주간 스케줄 조회
response = requests.get('http://localhost:5000/api/schedule/week/팀ID/스케줄ID/2025-04-07')

3. 일간 스케줄 조회
response = requests.get('http://localhost:5000/api/schedule/day/팀ID/스케줄ID/2025-04-07')

4. 스케줄 추가
response = requests.post('http://localhost:5000/api/schedule/add', json={
    "teamId": "팀ID",
    "scheduleId": "스케줄ID",
    "entries": [{
        "name": "홍길동",
        "date": "2025-04-07",
        "dayOfWeek": "월",
        "startTime": "09:00",
        "endTime": "18:00",
        "hourPrice": 9620,
        "overtime": False,
        "night": False,
        "Holiday": False
    }]
})

5. 스케줄 수정
response = requests.put('http://localhost:5000/api/schedule/update', json={
    "teamId": "팀ID",
    "scheduleId": "스케줄ID",
    "entries": [{
        "id": "엔트리ID",
        "payInfo": "급여정보ID",
        "name": "홍길동",
        "date": "2025-04-07",
        "startTime": "10:00",
        "endTime": "19:00"
    }]
})

6. 스케줄 삭제
response = requests.delete('http://localhost:5000/api/schedule/delete', json={
    "teamId": "팀ID",
    "scheduleId": "스케줄ID",
    "entryIds": ["엔트리ID1", "엔트리ID2"]
})

7. 급여 계산
response = requests.get('http://localhost:5000/api/salary/사용자ID?period_type=month&date=2025-04')
response = requests.get('http://localhost:5000/api/salary/사용자ID?period_type=week&date=2025-04-07')
"""

def getMonthSchedule(teamId, scheduleId, date):
    """
    월간 팀 스케줄을 조회합니다.
    
    Args:
        teamId (str): 팀 ID
        scheduleId (str): 스케줄 ID
        date (str): 조회할 년월 (예: "2025-04")
    
    Returns:
        dict: 성공 시 {"success": True, "entries": [...]} 형태로 반환
              실패 시 {"error": "에러 메시지"} 형태로 반환
    """
    try:
        # date 형식: "2025-04"
        year_month = datetime.strptime(date, "%Y-%m")
        next_month = year_month.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        
        start_date = year_month.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")
        
        result = supabase.table("t_entry").select(
            "*",
            "t_payinfo(*)"
        ).eq("teamId", teamId).eq("schedule_id", scheduleId)\
         .gte("date", start_date).lte("date", end_date).execute()
        
        return {"success": True, "entries": result.data}
    except Exception as e:
        return {"error": str(e)}

def getWeekSchedule(teamId, scheduleId, date):
    try:
        # date 형식: "2025-04-07" (월요일)
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = start_date + timedelta(days=6)
        
        result = supabase.table("t_entry").select(
            "*",
            "t_payinfo(*)"
        ).eq("teamId", teamId).eq("schedule_id", scheduleId)\
         .gte("date", start_date.strftime("%Y-%m-%d"))\
         .lte("date", end_date.strftime("%Y-%m-%d")).execute()
        
        return {"success": True, "entries": result.data}
    except Exception as e:
        return {"error": str(e)}

def getDaySchedule(teamId, scheduleId, date):
    try:
        # date 형식: "2025-04-07"
        result = supabase.table("t_entry").select(
            "*",
            "t_payinfo(*)"
        ).eq("teamId", teamId).eq("schedule_id", scheduleId)\
         .eq("date", date).execute()
        
        return {"success": True, "entries": result.data}
    except Exception as e:
        return {"error": str(e)}

def addSchedule(teamId, scheduleId, entries):
    try:
        inserted_entries = []
        for entry in entries:
            payinfo_id = str(uuid.uuid4())
            
            # PayInfo 추가
            payinfo = {
                "id": payinfo_id,
                "teamId": teamId,
                "hourPrice": entry.get("hourPrice", 0),
                "wHoliday": entry.get("wHoliday", False),
                "Holiday": entry.get("Holiday", False),
                "overtime": entry.get("overtime", False),
                "night": entry.get("night", False),
                "duty": entry.get("duty", "")
            }
            supabase.table("t_payinfo").insert(payinfo).execute()
            
            # Entry 추가
            entry_data = {
                "id": str(uuid.uuid4()),
                "teamId": teamId,
                "schedule_id": scheduleId,
                "name": entry["name"],
                "nameById": entry.get("nameById", ""),
                "date": entry["date"],
                "dayOfWeek": entry["dayOfWeek"],
                "startTime": entry["startTime"],
                "endTime": entry["endTime"],
                "payInfo": payinfo_id
            }
            result = supabase.table("t_entry").insert(entry_data).execute()
            inserted_entries.append(result.data[0])
            
        return {"success": True, "entries": inserted_entries}
    except Exception as e:
        return {"error": str(e)}

def updateSchedule(teamId, scheduleId, entries):
    try:
        updated_entries = []
        for entry in entries:
            entry_id = entry.get("id")
            if not entry_id:
                continue
                
            # PayInfo 업데이트
            payinfo = {
                "hourPrice": entry.get("hourPrice", 0),
                "wHoliday": entry.get("wHoliday", False),
                "Holiday": entry.get("Holiday", False),
                "overtime": entry.get("overtime", False),
                "night": entry.get("night", False),
                "duty": entry.get("duty", "")
            }
            supabase.table("t_payinfo").update(payinfo)\
                .eq("id", entry["payInfo"]).execute()
            
            # Entry 업데이트
            entry_data = {
                "name": entry["name"],
                "nameById": entry.get("nameById", ""),
                "date": entry["date"],
                "dayOfWeek": entry["dayOfWeek"],
                "startTime": entry["startTime"],
                "endTime": entry["endTime"]
            }
            result = supabase.table("t_entry").update(entry_data)\
                .eq("id", entry_id).eq("teamId", teamId)\
                .eq("schedule_id", scheduleId).execute()
            updated_entries.append(result.data[0])
            
        return {"success": True, "entries": updated_entries}
    except Exception as e:
        return {"error": str(e)}

def deleteSchedule(teamId, scheduleId, entryIds):
    try:
        # 먼저 PayInfo IDs 가져오기
        entries = supabase.table("t_entry").select("payInfo")\
            .eq("teamId", teamId).eq("schedule_id", scheduleId)\
            .in_("id", entryIds).execute()
        
        payinfo_ids = [entry["payInfo"] for entry in entries.data]
        
        # Entry 삭제
        supabase.table("t_entry").delete()\
            .eq("teamId", teamId).eq("schedule_id", scheduleId)\
            .in_("id", entryIds).execute()
            
        # PayInfo 삭제
        supabase.table("t_payinfo").delete()\
            .in_("id", payinfo_ids).execute()
        
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

def calculateUserSalary(userId, period_type, date=None):
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m")
            
        if period_type not in ['week', 'month']:
            return {"error": "유효하지 않은 기간 타입입니다."}
            
        # 기간 설정
        if period_type == 'month':
            year_month = datetime.strptime(date, "%Y-%m")
            next_month = year_month.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            start_date = year_month.strftime("%Y-%m-%d")
            end_date = last_day.strftime("%Y-%m-%d")
        else:  # week
            start_date = datetime.strptime(date, "%Y-%m-%d")
            end_date = start_date + timedelta(days=6)
            start_date = start_date.strftime("%Y-%m-%d")
            end_date = end_date.strftime("%Y-%m-%d")
        
        # 개인 스케줄 급여 계산
        i_entries = supabase.table("i_entry").select(
            "*",
            "i_payinfo(*)"
        ).eq("nameById", userId)\
         .gte("date", start_date).lte("date", end_date).execute()
         
        # 팀 스케줄 급여 계산
        t_entries = supabase.table("t_entry").select(
            "*",
            "t_payinfo(*)"
        ).eq("nameById", userId)\
         .gte("date", start_date).lte("date", end_date).execute()
        
        total_salary = 0
        entries_with_salary = []
        
        # 급여 계산 함수
        def calculate_entry_salary(entry, payinfo):
            start = datetime.strptime(entry["startTime"], "%H:%M")
            end = datetime.strptime(entry["endTime"], "%H:%M")
            hours = (end - start).seconds / 3600
            
            base_salary = hours * payinfo["hourPrice"]
            
            # 각종 수당 계산
            if payinfo["overtime"]:
                base_salary *= 1.5
            if payinfo["night"]:
                base_salary *= 1.2
            if payinfo["Holiday"]:
                base_salary *= 1.5
                
            return base_salary
        
        # 개인 스케줄 급여 계산
        for entry in i_entries.data:
            salary = calculate_entry_salary(entry, entry["i_payinfo"])
            total_salary += salary
            entries_with_salary.append({
                **entry,
                "calculated_salary": salary
            })
            
        # 팀 스케줄 급여 계산
        for entry in t_entries.data:
            salary = calculate_entry_salary(entry, entry["t_payinfo"])
            total_salary += salary
            entries_with_salary.append({
                **entry,
                "calculated_salary": salary
            })
        
        return {
            "success": True,
            "total_salary": total_salary,
            "entries": entries_with_salary,
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "type": period_type
            }
        }
    except Exception as e:
        return {"error": str(e)}

# === 개인 스케줄 관리 함수 ===
"""
개인 스케줄 관리 함수들의 사용 예시:

1. 월간 개인 스케줄 조회
response = requests.get('http://localhost:5000/api/personal-schedule/month/사용자ID/2025-04')

2. 주간 개인 스케줄 조회
response = requests.get('http://localhost:5000/api/personal-schedule/week/사용자ID/2025-04-07')

3. 일간 개인 스케줄 조회
response = requests.get('http://localhost:5000/api/personal-schedule/day/사용자ID/2025-04-07')

4. 개인 스케줄 추가
response = requests.post('http://localhost:5000/api/personal-schedule/add', json={
    "userId": "사용자ID",
    "entries": [{
        "name": "개인 스케줄",
        "date": "2025-04-07",
        "dayOfWeek": "월",
        "startTime": "09:00",
        "endTime": "18:00",
        "hourPrice": 9620,
        "overtime": False,
        "night": False,
        "Holiday": False
    }]
})

5. 개인 스케줄 수정
response = requests.put('http://localhost:5000/api/personal-schedule/update', json={
    "userId": "사용자ID",
    "entries": [{
        "id": "엔트리ID",
        "payInfo": "급여정보ID",
        "name": "수정된 스케줄",
        "date": "2025-04-07",
        "startTime": "10:00",
        "endTime": "19:00"
    }]
})

6. 개인 스케줄 삭제
response = requests.delete('http://localhost:5000/api/personal-schedule/delete', json={
    "userId": "사용자ID",
    "entryIds": ["엔트리ID1", "엔트리ID2"]
})

7. 개인 급여 계산
response = requests.get('http://localhost:5000/api/personal-salary/사용자ID?period_type=month&date=2025-04')
response = requests.get('http://localhost:5000/api/personal-salary/사용자ID?period_type=week&date=2025-04-07')
"""

def getPersonalMonthSchedule(userId, date):
    """
    월간 개인 스케줄을 조회합니다.
    
    Args:
        userId (str): 사용자 ID
        date (str): 조회할 년월 (예: "2025-04")
    
    Returns:
        dict: 성공 시 {"success": True, "entries": [...]} 형태로 반환
              실패 시 {"error": "에러 메시지"} 형태로 반환
    """
    try:
        # date 형식: "2025-04"
        year_month = datetime.strptime(date, "%Y-%m")
        next_month = year_month.replace(day=28) + timedelta(days=4)
        last_day = next_month - timedelta(days=next_month.day)
        
        start_date = year_month.strftime("%Y-%m-%d")
        end_date = last_day.strftime("%Y-%m-%d")
        
        result = supabase.table("i_entry").select(
            "*",
            "i_payinfo(*)"
        ).eq("userId", userId)\
         .gte("date", start_date).lte("date", end_date).execute()
        
        return {"success": True, "entries": result.data}
    except Exception as e:
        return {"error": str(e)}

def getPersonalWeekSchedule(userId, date):
    """
    주간 개인 스케줄을 조회합니다.
    
    Args:
        userId (str): 사용자 ID
        date (str): 조회할 날짜 (예: "2025-04-07", 월요일 기준)
    
    Returns:
        dict: 성공 시 {"success": True, "entries": [...]} 형태로 반환
              실패 시 {"error": "에러 메시지"} 형태로 반환
    """
    try:
        # date 형식: "2025-04-07" (월요일)
        start_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = start_date + timedelta(days=6)
        
        result = supabase.table("i_entry").select(
            "*",
            "i_payinfo(*)"
        ).eq("userId", userId)\
         .gte("date", start_date.strftime("%Y-%m-%d"))\
         .lte("date", end_date.strftime("%Y-%m-%d")).execute()
        
        return {"success": True, "entries": result.data}
    except Exception as e:
        return {"error": str(e)}

def getPersonalDaySchedule(userId, date):
    """
    일간 개인 스케줄을 조회합니다.
    
    Args:
        userId (str): 사용자 ID
        date (str): 조회할 날짜 (예: "2025-04-07")
    
    Returns:
        dict: 성공 시 {"success": True, "entries": [...]} 형태로 반환
              실패 시 {"error": "에러 메시지"} 형태로 반환
    """
    try:
        # date 형식: "2025-04-07"
        result = supabase.table("i_entry").select(
            "*",
            "i_payinfo(*)"
        ).eq("userId", userId)\
         .eq("date", date).execute()
        
        return {"success": True, "entries": result.data}
    except Exception as e:
        return {"error": str(e)}

def addPersonalSchedule(userId, entries):
    """
    개인 스케줄을 추가합니다.
    
    Args:
        userId (str): 사용자 ID
        entries (list): 추가할 스케줄 항목들의 리스트
            각 항목은 다음 필드를 포함해야 함:
            - name: 스케줄 이름
            - date: 날짜 (YYYY-MM-DD)
            - dayOfWeek: 요일
            - startTime: 시작 시간 (HH:MM)
            - endTime: 종료 시간 (HH:MM)
            - hourPrice: 시급
            - overtime: 초과근무 여부
            - night: 야간근무 여부
            - Holiday: 휴일근무 여부
    
    Returns:
        dict: 성공 시 {"success": True, "entries": [...]} 형태로 반환
              실패 시 {"error": "에러 메시지"} 형태로 반환
    """
    try:
        inserted_entries = []
        for entry in entries:
            payinfo_id = str(uuid.uuid4())
            
            # PayInfo 추가
            payinfo = {
                "id": payinfo_id,
                "userId": userId,
                "hourPrice": entry.get("hourPrice", 0),
                "wHoliday": entry.get("wHoliday", False),
                "Holiday": entry.get("Holiday", False),
                "overtime": entry.get("overtime", False),
                "night": entry.get("night", False),
                "duty": entry.get("duty", "")
            }
            supabase.table("i_payinfo").insert(payinfo).execute()
            
            # Entry 추가
            entry_data = {
                "id": str(uuid.uuid4()),
                "userId": userId,
                "name": entry["name"],
                "date": entry["date"],
                "dayOfWeek": entry["dayOfWeek"],
                "startTime": entry["startTime"],
                "endTime": entry["endTime"],
                "payInfo": payinfo_id
            }
            result = supabase.table("i_entry").insert(entry_data).execute()
            inserted_entries.append(result.data[0])
            
        return {"success": True, "entries": inserted_entries}
    except Exception as e:
        return {"error": str(e)}

def updatePersonalSchedule(userId, entries):
    """
    개인 스케줄을 수정합니다.
    
    Args:
        userId (str): 사용자 ID
        entries (list): 수정할 스케줄 항목들의 리스트
            각 항목은 다음 필드를 포함해야 함:
            - id: 엔트리 ID
            - payInfo: 급여정보 ID
            - name: 스케줄 이름
            - date: 날짜 (YYYY-MM-DD)
            - startTime: 시작 시간 (HH:MM)
            - endTime: 종료 시간 (HH:MM)
    
    Returns:
        dict: 성공 시 {"success": True, "entries": [...]} 형태로 반환
              실패 시 {"error": "에러 메시지"} 형태로 반환
    """
    try:
        updated_entries = []
        for entry in entries:
            entry_id = entry.get("id")
            if not entry_id:
                continue
                
            # PayInfo 업데이트
            payinfo = {
                "hourPrice": entry.get("hourPrice", 0),
                "wHoliday": entry.get("wHoliday", False),
                "Holiday": entry.get("Holiday", False),
                "overtime": entry.get("overtime", False),
                "night": entry.get("night", False),
                "duty": entry.get("duty", "")
            }
            supabase.table("i_payinfo").update(payinfo)\
                .eq("id", entry["payInfo"]).execute()
            
            # Entry 업데이트
            entry_data = {
                "name": entry["name"],
                "date": entry["date"],
                "dayOfWeek": entry["dayOfWeek"],
                "startTime": entry["startTime"],
                "endTime": entry["endTime"]
            }
            result = supabase.table("i_entry").update(entry_data)\
                .eq("id", entry_id).eq("userId", userId).execute()
            updated_entries.append(result.data[0])
            
        return {"success": True, "entries": updated_entries}
    except Exception as e:
        return {"error": str(e)}

def deletePersonalSchedule(userId, entryIds):
    """
    개인 스케줄을 삭제합니다.
    
    Args:
        userId (str): 사용자 ID
        entryIds (list): 삭제할 엔트리 ID들의 리스트
    
    Returns:
        dict: 성공 시 {"success": True} 형태로 반환
              실패 시 {"error": "에러 메시지"} 형태로 반환
    """
    try:
        # 먼저 PayInfo IDs 가져오기
        entries = supabase.table("i_entry").select("payInfo")\
            .eq("userId", userId)\
            .in_("id", entryIds).execute()
        
        payinfo_ids = [entry["payInfo"] for entry in entries.data]
        
        # Entry 삭제
        supabase.table("i_entry").delete()\
            .eq("userId", userId)\
            .in_("id", entryIds).execute()
            
        # PayInfo 삭제
        supabase.table("i_payinfo").delete()\
            .in_("id", payinfo_ids).execute()
        
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

def calculatePersonalSalary(userId, period_type, date=None):
    """
    개인 급여를 계산합니다.
    
    Args:
        userId (str): 사용자 ID
        period_type (str): 계산 기간 타입 ('week' 또는 'month')
        date (str, optional): 계산 기준 날짜
            - month인 경우: "YYYY-MM" 형식
            - week인 경우: "YYYY-MM-DD" 형식 (월요일 날짜)
            - 미지정시 현재 날짜 사용
    
    Returns:
        dict: 성공 시 {
            "success": True,
            "total_salary": 총급여,
            "entries": [...],
            "period": {
                "start_date": 시작일,
                "end_date": 종료일,
                "type": 기간타입
            }
        } 형태로 반환
        실패 시 {"error": "에러 메시지"} 형태로 반환
    """
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m")
            
        if period_type not in ['week', 'month']:
            return {"error": "유효하지 않은 기간 타입입니다."}
            
        # 기간 설정
        if period_type == 'month':
            year_month = datetime.strptime(date, "%Y-%m")
            next_month = year_month.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            start_date = year_month.strftime("%Y-%m-%d")
            end_date = last_day.strftime("%Y-%m-%d")
        else:  # week
            start_date = datetime.strptime(date, "%Y-%m-%d")
            end_date = start_date + timedelta(days=6)
            start_date = start_date.strftime("%Y-%m-%d")
            end_date = end_date.strftime("%Y-%m-%d")
        
        # 개인 스케줄 급여 계산
        entries = supabase.table("i_entry").select(
            "*",
            "i_payinfo(*)"
        ).eq("userId", userId)\
         .gte("date", start_date).lte("date", end_date).execute()
         
        total_salary = 0
        entries_with_salary = []
        
        # 급여 계산 함수
        def calculate_entry_salary(entry, payinfo):
            start = datetime.strptime(entry["startTime"], "%H:%M")
            end = datetime.strptime(entry["endTime"], "%H:%M")
            hours = (end - start).seconds / 3600
            
            base_salary = hours * payinfo["hourPrice"]
            
            # 각종 수당 계산
            if payinfo["overtime"]:
                base_salary *= 1.5
            if payinfo["night"]:
                base_salary *= 1.2
            if payinfo["Holiday"]:
                base_salary *= 1.5
                
            return base_salary
        
        # 급여 계산
        for entry in entries.data:
            salary = calculate_entry_salary(entry, entry["i_payinfo"])
            total_salary += salary
            entries_with_salary.append({
                **entry,
                "calculated_salary": salary
            })
        
        return {
            "success": True,
            "total_salary": total_salary,
            "entries": entries_with_salary,
            "period": {
                "start_date": start_date,
                "end_date": end_date,
                "type": period_type
            }
        }
    except Exception as e:
        return {"error": str(e)}

# === HTML ===
HTML = '''
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>분리된 입력</title>
<script src="https://accounts.google.com/gsi/client" async defer></script>
</head><body>

{% if not session.get("user") %}
<h2>🔐 구글 로그인</h2>
<div id="g_id_onload"
     data-client_id="YOUR_GOOGLE_CLIENT_ID"
     data-callback="handleCredentialResponse">
</div>
<div class="g_id_signin" data-type="standard"></div>

<script>
function handleCredentialResponse(response) {
    fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ id_token: response.credential })
    }).then(r => {
        if (r.redirected) {
            window.location.href = r.url;
        } else {
            r.text().then(alert);
        }
    });
}
</script>

{% else %}
<h3>환영합니다 {{ session['user']['name'] }}</h3>
<a href="/logout">로그아웃</a><hr>

<h2>👤 개인 시간표 추가</h2>
<form method="POST" action="/add-i-schedule">
  제목: <input name="i_title"><br>
  시작일: <input name="i_start_date" type="date"><br>
  종료일: <input name="i_end_date" type="date"><br>
  이름: <input name="i_name"><br>
  날짜: <input name="i_date" type="date"><br>
  요일: <input name="i_day"><br>
  시작: <input name="i_start_time" type="time">
  종료: <input name="i_end_time" type="time"><br>
  시급: <input name="i_hour_price" type="number"><br>
  주휴 <input type="checkbox" name="i_w_holiday"> 
  공휴일 <input type="checkbox" name="i_holiday">
  초과 <input type="checkbox" name="i_overtime"> 
  야간 <input type="checkbox" name="i_night"><br>
  세금: <input name="i_duty"><br>
  <input type="submit" value="개인 시간표 추가">
</form>

<h2>👥 팀 시간표 추가</h2>
<form method="POST" action="/add-t-schedule">
  팀 ID: <input name="t_team_id"><br>
  제목: <input name="t_title"><br>
  시작일: <input name="t_start_date" type="date">
  종료일: <input name="t_end_date" type="date"><br>
  이름: <input name="t_name"><br>
  날짜: <input name="t_date" type="date">
  요일: <input name="t_day"><br>
  시작: <input name="t_start_time" type="time">
  종료: <input name="t_end_time" type="time"><br>
  시급: <input name="t_hour_price" type="number"><br>
  주휴 <input type="checkbox" name="t_w_holiday"> 
  공휴일 <input type="checkbox" name="t_holiday">
  초과 <input type="checkbox" name="t_overtime"> 
  야간 <input type="checkbox" name="t_night"><br>
  세금: <input name="t_duty"><br>
  <input type="submit" value="팀 시간표 추가">
</form>

<h2>📝 게시글 추가</h2>
<form method="POST" action="/add-post">
  타입(공지/일반): <input name="post_type"><br>
  제목: <input name="post_title"><br>
  내용: <textarea name="post_content"></textarea><br>
  <input type="submit" value="게시글 추가">
</form>
{% endif %}

</body></html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/login', methods=['POST'])
def login():
    id_token = request.form.get("id_token")
    if not id_token:
        return "id_token 필요", 400
    
    user_info = verify_google_token(id_token)
    if not user_info:
        return "구글 토큰 검증 실패", 400
    
    user_id = user_info["sub"]
    
    # user 테이블에 sub를 id로 사용해 검색
    result = supabase.table("user").select("*").eq("id", user_id).execute()
    if result.data:
        user = result.data[0]
    else:
        # 신규 사용자 등록
        insert_res = supabase.table("user").insert({
            "id": user_id,
            "sub": user_info["sub"],
            "email": user_info["email"],
            "name": user_info["name"]
        }).execute()
        if insert_res.status_code != 201:
            return "사용자 생성 실패", 500
        user = {
            "id": user_id,
            "sub": user_info["sub"],
            "email": user_info["email"],
            "name": user_info["name"]
        }
    session['user'] = user
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/add-i-schedule', methods=['POST'])
def add_i_schedule():
    user = session.get("user")
    if not user:
        return redirect('/')
    uid = user["id"]
    i_schedule_id, i_entry_id, i_payinfo_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())

    supabase.table("i_schedule").insert({
        "id": i_schedule_id,
        "userId": uid,
        "title": request.form["i_title"],
        "startDate": safe_date(request.form["i_start_date"]),
        "endDate": safe_date(request.form["i_end_date"])
    }).execute()
    supabase.table("i_payinfo").insert({
        "id": i_payinfo_id,
        "userId": uid,
        "hourPrice": safe_int(request.form["i_hour_price"]),
        "wHoliday": safe_bool(request.form.get("i_w_holiday")),
        "Holiday": safe_bool(request.form.get("i_holiday")),
        "overtime": safe_bool(request.form.get("i_overtime")),
        "night": safe_bool(request.form.get("i_night")),
        "duty": request.form["i_duty"]
    }).execute()
    supabase.table("i_entry").insert({
        "id": i_entry_id,
        "userId": uid,
        "name": request.form["i_name"],
        "nameById": uid,
        "date": safe_date(request.form["i_date"]),
        "dayOfWeek": request.form["i_day"],
        "startTime": request.form["i_start_time"],
        "endTime": request.form["i_end_time"],
        "payInfo": i_payinfo_id
    }).execute()
    return redirect('/')

@app.route('/add-t-schedule', methods=['POST'])
def add_t_schedule():
    user = session.get("user")
    if not user:
        return redirect('/')
    uid = user["id"]
    t_schedule_id, t_entry_id, t_payinfo_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    team_id = request.form["t_team_id"]

    supabase.table("t_schedule").insert({
        "id": t_schedule_id,
        "teamId": team_id,
        "title": request.form["t_title"],
        "startDate": safe_date(request.form["t_start_date"]),
        "endDate": safe_date(request.form["t_end_date"])
    }).execute()
    supabase.table("t_payinfo").insert({
        "id": t_payinfo_id,
        "teamId": team_id,
        "hourPrice": safe_int(request.form["t_hour_price"]),
        "wHoliday": safe_bool(request.form.get("t_w_holiday")),
        "Holiday": safe_bool(request.form.get("t_holiday")),
        "overtime": safe_bool(request.form.get("t_overtime")),
        "night": safe_bool(request.form.get("t_night")),
        "duty": request.form["t_duty"]
    }).execute()
    supabase.table("t_entry").insert({
        "id": t_entry_id,
        "teamId": team_id,
        "schedule_id": t_schedule_id,
        "name": request.form["t_name"],
        "nameById": uid,
        "date": safe_date(request.form["t_date"]),
        "dayOfWeek": request.form["t_day"],
        "startTime": request.form["t_start_time"],
        "endTime": request.form["t_end_time"],
        "payInfo": t_payinfo_id
    }).execute()
    return redirect('/')

@app.route('/add-post', methods=['POST'])
def add_post():
    user = session.get("user")
    if not user:
        return redirect('/')
    name = user["name"]
    post_id = str(uuid.uuid4())

    supabase.table("post").insert({
        "id": post_id,
        "type": request.form["post_type"],
        "title": request.form["post_title"],
        "content": request.form["post_content"],
        "author": name,
        "createdAt": datetime.utcnow().isoformat(),
        "comments": []
    }).execute()
    return redirect('/')

# === 새로운 인증 API 엔드포인트 ===
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return {"error": "이메일과 비밀번호가 필요합니다."}, 400
    
    result = registerUser(data)
    if "error" in result:
        return result, 400
    return result

@app.route('/api/login', methods=['POST'])
def login_email():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return {"error": "이메일과 비밀번호가 필요합니다."}, 400
    
    result = loginUser(data['email'], data['password'])
    if "error" in result:
        return result, 401
    return result

@app.route('/api/token-login', methods=['POST'])
def login_token():
    data = request.get_json()
    if not data or not data.get('token'):
        return {"error": "토큰이 필요합니다."}, 400
    
    result = loginByToken(data['token'])
    if "error" in result:
        return result, 401
    return result

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    result = getUserById(user_id)
    if "error" in result:
        return result, 404
    return result

@app.route('/api/logout', methods=['POST'])
def logout():
    result = logoutUser()
    if "error" in result:
        return result, 500
    return result

# === 스케줄 관리 API 엔드포인트 ===
@app.route('/api/schedule/month/<team_id>/<schedule_id>/<date>')
def get_month_schedule(team_id, schedule_id, date):
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    result = getMonthSchedule(team_id, schedule_id, date)
    if "error" in result:
        return result, 400
    return result

@app.route('/api/schedule/week/<team_id>/<schedule_id>/<date>')
def get_week_schedule(team_id, schedule_id, date):
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    result = getWeekSchedule(team_id, schedule_id, date)
    if "error" in result:
        return result, 400
    return result

@app.route('/api/schedule/day/<team_id>/<schedule_id>/<date>')
def get_day_schedule(team_id, schedule_id, date):
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    result = getDaySchedule(team_id, schedule_id, date)
    if "error" in result:
        return result, 400
    return result

@app.route('/api/schedule/add', methods=['POST'])
def add_schedule_entries():
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    data = request.get_json()
    if not data or not data.get('teamId') or not data.get('scheduleId') or not data.get('entries'):
        return {"error": "필수 데이터가 누락되었습니다."}, 400
    
    result = addSchedule(data['teamId'], data['scheduleId'], data['entries'])
    if "error" in result:
        return result, 400
    return result

@app.route('/api/schedule/update', methods=['PUT'])
def update_schedule_entries():
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    data = request.get_json()
    if not data or not data.get('teamId') or not data.get('scheduleId') or not data.get('entries'):
        return {"error": "필수 데이터가 누락되었습니다."}, 400
    
    result = updateSchedule(data['teamId'], data['scheduleId'], data['entries'])
    if "error" in result:
        return result, 400
    return result

@app.route('/api/schedule/delete', methods=['DELETE'])
def delete_schedule_entries():
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    data = request.get_json()
    if not data or not data.get('teamId') or not data.get('scheduleId') or not data.get('entryIds'):
        return {"error": "필수 데이터가 누락되었습니다."}, 400
    
    result = deleteSchedule(data['teamId'], data['scheduleId'], data['entryIds'])
    if "error" in result:
        return result, 400
    return result

@app.route('/api/salary/<user_id>')
def get_user_salary(user_id):
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    period_type = request.args.get('period_type', 'month')
    date = request.args.get('date')
    
    result = calculateUserSalary(user_id, period_type, date)
    if "error" in result:
        return result, 400
    return result

# === 개인 스케줄 API 엔드포인트 ===
@app.route('/api/personal-schedule/month/<user_id>/<date>')
def get_personal_month_schedule(user_id, date):
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    result = getPersonalMonthSchedule(user_id, date)
    if "error" in result:
        return result, 400
    return result

@app.route('/api/personal-schedule/week/<user_id>/<date>')
def get_personal_week_schedule(user_id, date):
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    result = getPersonalWeekSchedule(user_id, date)
    if "error" in result:
        return result, 400
    return result

@app.route('/api/personal-schedule/day/<user_id>/<date>')
def get_personal_day_schedule(user_id, date):
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    result = getPersonalDaySchedule(user_id, date)
    if "error" in result:
        return result, 400
    return result

@app.route('/api/personal-schedule/add', methods=['POST'])
def add_personal_schedule_entries():
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    data = request.get_json()
    if not data or not data.get('userId') or not data.get('entries'):
        return {"error": "필수 데이터가 누락되었습니다."}, 400
    
    result = addPersonalSchedule(data['userId'], data['entries'])
    if "error" in result:
        return result, 400
    return result

@app.route('/api/personal-schedule/update', methods=['PUT'])
def update_personal_schedule_entries():
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    data = request.get_json()
    if not data or not data.get('userId') or not data.get('entries'):
        return {"error": "필수 데이터가 누락되었습니다."}, 400
    
    result = updatePersonalSchedule(data['userId'], data['entries'])
    if "error" in result:
        return result, 400
    return result

@app.route('/api/personal-schedule/delete', methods=['DELETE'])
def delete_personal_schedule_entries():
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    data = request.get_json()
    if not data or not data.get('userId') or not data.get('entryIds'):
        return {"error": "필수 데이터가 누락되었습니다."}, 400
    
    result = deletePersonalSchedule(data['userId'], data['entryIds'])
    if "error" in result:
        return result, 400
    return result

@app.route('/api/personal-salary/<user_id>')
def get_personal_salary(user_id):
    if not session.get('user'):
        return {"error": "로그인이 필요합니다."}, 401
    
    period_type = request.args.get('period_type', 'month')
    date = request.args.get('date')
    
    result = calculatePersonalSalary(user_id, period_type, date)
    if "error" in result:
        return result, 400
    return result

if __name__ == '__main__':
    app.run(debug=True)
