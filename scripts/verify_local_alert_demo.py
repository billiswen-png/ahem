"""Exercise demo-mode health -> notification -> incident entirely through UI."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

p=argparse.ArgumentParser()
p.add_argument('--identities',type=Path,required=True)
p.add_argument('--url',required=True)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
ids={a['id']:a for a in json.loads(args.identities.read_text())}
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome')
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' and '401' not in m.text else None)
    page.on('dialog',lambda d:d.accept())
    page.goto(args.url);assert page.title()=='Ahem 企業工作台'
    page.get_by_label('存取憑證').fill(ids['operator']['token'])
    page.get_by_role('button',name='進入工作台').click()
    expect(page.locator('#context')).to_contain_text('合成資料演練')
    page.get_by_role('button',name='通知規則',exact=True).click()
    row=page.locator('.row').filter(has=page.get_by_text('tts',exact=True))
    row.get_by_role('button',name='啟用規則').click()
    expect(row).to_contain_text('已啟用')
    page.screenshot(path=str(args.output/'rules.png'),full_page=True)
    def report(state):
        page.get_by_role('button',name='服務狀態',exact=True).click()
        page.get_by_label('演練服務').select_option('tts')
        page.get_by_label('演練狀態').select_option(state)
        page.get_by_role('button',name='送出合成狀態').click()
        expect(page.locator('#panel')).to_have_attribute('aria-busy','false')
    report('unavailable');report('unavailable')
    page.screenshot(path=str(args.output/'simulated-health.png'),full_page=True)
    page.get_by_role('button',name='站內通知',exact=True).click()
    expect(page.locator('tbody tr')).to_have_count(1)
    page.get_by_role('button',name='標示已讀').click()
    expect(page.locator('tbody')).to_contain_text('已讀')
    report('ok')
    page.get_by_role('button',name='站內通知',exact=True).click()
    expect(page.locator('tbody tr')).to_have_count(2)
    expect(page.locator('tbody')).to_contain_text('收到恢復正常回報')
    page.screenshot(path=str(args.output/'notifications.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(args.output/'notifications-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000})
    page.get_by_role('button',name='事故處理',exact=True).click()
    expect(page.locator('tbody tr')).to_have_count(1)
    page.get_by_role('button',name='確認事故').click()
    expect(page.locator('tbody')).to_contain_text('處理中')
    page.get_by_role('button',name='結案',exact=True).click()
    expect(page.locator('tbody')).to_contain_text('已結案')
    page.screenshot(path=str(args.output/'resolved-incident.png'),full_page=True)
    page.get_by_role('button',name='登出',exact=True).click()
    page.get_by_label('存取憑證').fill(ids['support']['token'])
    page.get_by_role('button',name='進入工作台').click()
    expect(page.locator('#workspace')).to_be_visible()
    assert page.get_by_role('button',name='通知規則',exact=True).count()==0
    page.get_by_role('button',name='站內通知',exact=True).click()
    expect(page.get_by_role('button',name='標示已讀')).to_have_count(2)
    assert errors==[],errors
    browser.close()
print('PASS: rules, synthetic reports, deduplication, recovery notification, independent read state, manual incident resolution, desktop/mobile, zero console/page errors; EXIT_CODE=0')
