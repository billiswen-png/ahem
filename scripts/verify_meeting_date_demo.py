"""Synthetic local demo: enter an actual-date field and verify derived metrics."""
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

p=argparse.ArgumentParser()
p.add_argument('--identities',type=Path,required=True)
p.add_argument('--url',required=True)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
actor=next(a for a in json.loads(args.identities.read_text()) if a['id']=='operator')
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome')
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' and '401' not in m.text else None)
    page.goto(args.url);assert page.title()=='Ahem 企業工作台'
    page.get_by_label('存取憑證').fill(actor['token'])
    page.get_by_role('button',name='進入工作台').click()
    page.get_by_role('button',name='內容與授權',exact=True).click()
    page.get_by_role('button',name='填寫日期',exact=True).first.click()
    page.get_by_label('會議日期',exact=True).fill(datetime.now(timezone.utc).date().isoformat())
    page.screenshot(path=str(args.output/'date-form.png'),full_page=True)
    page.get_by_role('button',name='儲存會議日期').click()
    expect(page.locator('.detail')).to_have_count(0)
    page.get_by_role('button',name='會議日期分析',exact=True).click()
    expect(page.locator('tbody tr')).to_have_count(1)
    page.get_by_label('分析期間').select_option('365')
    expect(page.locator('tbody tr')).to_have_count(1)
    expect(page.locator('#panel')).to_contain_text('管理員填寫')
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=str(args.output/'meeting-date-analysis.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(args.output/'meeting-date-mobile.png'),full_page=True)
    assert errors==[],errors
    browser.close()
print('PASS: enter date -> save -> date-based metrics -> 365-day filter; desktop/mobile, zero console/page errors; EXIT_CODE=0')
