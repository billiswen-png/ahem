"""Read-only UI verification of an isolated restored demo database."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

p=argparse.ArgumentParser()
p.add_argument('--identities',type=Path,required=True)
p.add_argument('--url',required=True)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args()
actor=next(x for x in json.loads(args.identities.read_text()) if x.get('regulated_content'))
args.output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome')
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' and '401' not in m.text else None)
    page.goto(args.url)
    assert page.title()=='Ahem 企業工作台'
    page.get_by_label('存取憑證').fill(actor['token'])
    page.get_by_role('button',name='進入工作台').click()
    expect(page.locator('#workspace')).to_be_visible()
    for title,filename in [('每日匯入統計','restored-trends.png'),('事故處理','restored-incidents.png')]:
        page.get_by_role('button',name=title,exact=True).click()
        expect(page.locator('#panel')).to_have_attribute('aria-busy','false')
        page.screenshot(path=str(args.output/filename),full_page=True)
    page.get_by_role('button',name='內容與授權',exact=True).click()
    row=page.locator('tbody tr').filter(has_text='受限內容').first
    row.get_by_role('button',name='查看內容').click()
    page.get_by_role('button',name='確認讀取').click()
    expect(page.locator('.transcript')).to_contain_text('先回到第二季上線排程')
    page.screenshot(path=str(args.output/'restored-content.png'),full_page=True)
    assert errors==[],errors
    print('PASS: restored login, trends, incidents and authorized encrypted content; zero page/console errors; exit 0')
    browser.close()
