#import win32com.client as win32
#import win32gui
from time import sleep
from datetime import datetime
from pythoncom import CoInitialize

def recreateHwp(master_file_name, new_file_name, replace_text_list):

    #hwp = win32.gencache.EnsureDispatch('HWPFrame.HwpObject',CoInitialize())
    #hwp = win32.dynamic.Dispatch('HWPFrame.HwpObject')
    #hwp.XHwpWindows.Item(0).Visible = True
    hwp.RegisterModule('FilePathCheckDLL','FilePathCheckerModuleExample')
    hwp.Open(master_file_name,'HWP','forceopen:true')

    for t in replace_text_list:
        hwp.HAction.GetDefault('AllReplace', hwp.HParameterSet.HFindReplace.HSet)
        option=hwp.HParameterSet.HFindReplace
        option.FindString=t[0]
        option.ReplaceString=t[1]
        option.IgnoreMessage=1
        hwp.HAction.Execute('AllReplace', hwp.HParameterSet.HFindReplace.HSet)

    hwp.SaveAs(new_file_name)

    hwp.Clear(3)
    hwp.Quit()
    sleep(0.5)

if __name__ == "__main__":

    now = datetime.now()
    ymd = now.strftime("%Y%m%d")

    #일일 점검결과
    master_file_name = 'C:\\Users\\KDB\\Downloads\\일일 점검결과_template.hwp'
    new_file_name = 'C:\\Users\\KDB\\Downloads\\일일 점검결과'+'_'+ymd+'.hwp'

    t_date = now.strftime("%Y.%m.%d")[2:]
    t_dayoff = '김형기, 허재영'
    t_education = ''
    t_description = ''

    replace_text_list=[
        ('<<date>>',t_date),
        ('<<description>>', t_description),
        ('<<vacation>>',t_dayoff),
        ('<<education>>',t_education),
    ]

    recreateHwp(master_file_name, new_file_name, replace_text_list)

    #일일 점검결과
    master_file_name = 'C:\\Users\\KDB\\Downloads\\시스템 작업 보고_template.hwp'
    new_file_name = 'C:\\Users\\KDB\\Downloads\\시스템 작업 보고'+'_'+ymd+'.hwp'

    t_date = now.strftime("%m/%d")
    t_description = """
    자산유동화수탁 운영WAS 재가동
    - 작업내용 : SR반영 (서버 : utc05a)
    - 작업시간 : 9/29, 18:00 ~ 19:00
    - 작업자 : 미들웨어 최용타, 트레이딩팀 정태섭
    - 영향도 : 재가동시 서비스 순단

    UMS 운영WAS 재가동
    - 작업내용 : UMS 시스템 SWAP 메모리 클리어를 위한 재가동
    - 작업시간 : 9/29, 18:00 ~ 19:00
    - 작업자 : 미들웨어 윤연상, DBA 전상현
    - 영향도 : 롤링 재가동 서비스 중단 없음 ( 업무팀과 협의 완료 )
    """

    replace_text_list=[
        ('<<date>>',t_date),
        ('<<description>>', t_description)
    ]

    recreateHwp(master_file_name, new_file_name, replace_text_list)