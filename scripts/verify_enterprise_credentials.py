"""Synthetic-only create/rotate demo. Never print or screenshot credentials."""
import argparse
import json
import secrets
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

p=argparse.ArgumentParser()
p.add_argument('--identities',type=Path,required=True)
p.add_argument('--url',required=True)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
ids=json.loads(args.identities.read_text())
admin=next(a for a in ids if a['id']=='operator')
name='demo-'+secrets.token_hex(4)
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome')
    context=browser.new_context(viewport={'width':1440,'height':1000})
    page=context.new_page();errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:errors.append(m.text) if m.type=='error' and '401' not in m.text else None)
    page.on('dialog',lambda d:d.accept())
    page.goto(args.url)
    assert page.title()=='Ahem 企業工作台'
    page.get_by_label('存取憑證').fill(admin['token'])
    page.get_by_role('button',name='進入工作台').click()
    page.get_by_role('button',name='成員工作階段',exact=True).click()
    page.get_by_role('button',name='新增限時成員').click()
    expect(page.get_by_label('新增成員角色')).to_be_visible()
    page.screenshot(path=str(args.output/'create-form.png'),full_page=True)
    page.get_by_label('成員代碼').fill(name)
    page.get_by_label('憑證有效天數').fill('1')
    page.get_by_role('button',name='產生限時憑證').click()
    field=page.get_by_label('新存取憑證');expect(field).to_be_visible()
    expect(field).to_have_attribute('type','password')
    first=field.input_value()
    page.get_by_role('button',name='我已保存，關閉').click()
    row=page.locator('tbody tr').filter(has=page.get_by_text(name,exact=True))
    expect(row).to_contain_text('憑證到期')
    client=browser.new_context()
    def authenticate(token):
        return client.request.post(args.url.rstrip('/')+'/api/login',data={'token':token},headers={'Origin':args.url.rstrip('/')}).status
    assert authenticate(first)==200
    row.get_by_role('button',name='輪替憑證').click()
    page.get_by_role('button',name='確認撤銷舊憑證').click()
    expect(field).to_be_visible();second=field.input_value();assert first!=second
    page.get_by_role('button',name='我已保存，關閉').click()
    assert client.request.get(args.url.rstrip('/')+'/api/me').status==401
    assert authenticate(first)==401
    assert authenticate(second)==200
    # No screenshots until the one-time credential DOM has been removed.
    expect(page.get_by_label('新存取憑證')).to_have_count(0)
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=str(args.output/'members-rotated.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(args.output/'members-mobile.png'),full_page=True)
    row.get_by_role('button',name='停用成員').click()
    expect(row).to_contain_text('已停用')
    status=authenticate(second)
    assert status==401,f'Expected suspended login rejection 401, got {status}; run on an isolated demo without recent login tests'
    assert errors==[],errors
    browser.close()
print('PASS: create, masked one-time credential, login, rotate, old-key/session rejection, new-key login, suspension, desktop/mobile; zero page/console errors; EXIT_CODE=0')
