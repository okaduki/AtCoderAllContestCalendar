#!/usr/bin/env python3
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import datetime
from datetime import datetime, timedelta
import pytz
from time import sleep

import requests
import urllib
from bs4 import BeautifulSoup

ATCODER_URL = 'http://atcoder.jp?lang=ja'

def getContestSchedule():
    r = requests.get(ATCODER_URL)
    if r.status_code != 200:
        raise Exception('AtCoder returns ' + str(s.status_code))
    
    soup = BeautifulSoup(r.text, 'html5lib')
    next_contests = soup.find('h4', string='予定されたコンテスト')
    if not next_contests:
        return []

    contest_table = next_contests.find_next('table')
    if not contest_table:
        return []

    contest_contents = contest_table.find_all('td')
    if len(contest_contents) % 2 != 0: # 時間と名前の組になっているはず
        return []

    res = []
    for i in range(0, len(contest_contents), 2):
        res.append({
            'time': contest_contents[i].text,
            'summary': contest_contents[i+1].text,
            'url': contest_contents[i+1].a.get('href')
        })
        
    return res

def createEvent(summary, start, link):
    start_obj = {
        'dateTime': start.isoformat(),
        'timeZone': 'Asia/Tokyo',
    }

    # 終わり時間は取るのがめんどくさかったので嘘だと分かる10分にしとく
    end_obj = {
        'dateTime': (start + timedelta(minutes=10)).isoformat(),
        'timeZone': 'Asia/Tokyo',
    }

    obj = {
        'summary': summary,
        'start': start_obj,
        'end': end_obj,
        'description': link,
    }

    return obj

if __name__ == '__main__':
    # Setup the Calendar API
    SCOPES = 'https://www.googleapis.com/auth/calendar'
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        print('Error: credential is invalid or not found.')
        exit(1)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    # get target calendar
    clist_result = service.calendarList().list().execute()
    clist = clist_result.get('items', [])
    target_id = None
    for cl in clist:
        if 'AtCoderAllContest' == cl['summary']:
            target_id = cl['id']

    if target_id == None:
        print('Error: the calendar "AtCoderAllContest" was not found.')
        exit(1)

    # get list of registered contest
    now = datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
    clist = service.events().list(
        calendarId=target_id,
        orderBy='startTime',
        timeMin=now,
        singleEvents=True).execute().get('items', [])

    contests = getContestSchedule()

    for contest in contests:
        # すでに登録されてたら無視
        if contest['summary'] in [ev['summary'] for ev in clist]:
            continue
        
        t = datetime.strptime(contest['time'], '%Y/%m/%d %H:%M')
        ev = createEvent(contest['summary'], t, contest['url'])
        service.events().insert(calendarId=target_id, body=ev).execute()
        sleep(1)
