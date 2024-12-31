*DOMAIN                                                                                                            
KDB                                                                                                                
                                                                                                                   
*NODE                                                                                                              
pprmar11      WEBTOBDIR="/sw/webtob",                                                                              
              SHMKEY = 54000,                                                                                      
              DOCROOT="/sw/webtob/docs",                                                                           
              PORT = "15843",                                                                                      
              HTH = 1,                                                                                             
              Group = "wasgrp",                                                                                       
              User = "webtob",                                                                                     
              NODENAME = "$(NODENAME)",                                                                            
              ERRORDOCUMENT = "400,401,403,404,405,500,503",                                                       
                          METHOD = "GET, POST, HEAD, -OPTIONS",                                                    
                          CacheEntry = 0,                                                                          
              #Options="IgnoreExpect100Continue",                                                                  
                          UpperDirRestrict = Y,                                                                    
              JSVPORT = 19900,                                                                                     
              IPCPERM = 0777,                                                                                      
                          LOGPERM = 0640,                                                                          
              SERVICEORDER = "URI,EXT",                                                                            
              LOGGING = "acc_node",                                                                                
              ERRORLOG = "err_node",                                                                               
              SYSLOG = "syslog"                                                                                    
                                                                                                                   
*HTH_THREAD                                                                                                        
hth_worker                                                                                                         
              SendfileThreads = 4,                                                                                 
              AccessLogThread = Y,                                                                                 
              #ReadBufSize=1048576, #1M                                                                            
              #HtmlsCompression="text/html",                                                                       
              SendfileThreshold=0,                                                                                 
              WorkerThreads=8                                                                                      
                                                                                                                   
                                                                                                                   
*VHOST                                                                                                             
v_PMS         DOCROOT="/app/wisepms/webdoc/wisepms_dev",                                                           
              HOSTNAME = "pmp.kdb.co.kr",                                                                            
              PORT = "20083",                                                                                      
              ERRORDOCUMENT = "400,401,403,404,405,500,503",                                                       
              METHOD = "GET, POST, HEAD, -OPTIONS",                                                                
              SERVICEORDER = "URI,EXT",                                                                            
              LOGGING = "acc_PMS",                                                                                 
              ERRORLOG = "err_PMS"                                                                                 
                                                                                                                   
v_PMS_S       DOCROOT="/app/wisepms/webdoc/wisepms_dev",                                                           
              HOSTNAME = "pmp.kdb.co.kr",                                                                         
              PORT = "20443",                                                                                      
              ERRORDOCUMENT = "400,401,403,404,405,500,503",                                                       
              METHOD = "GET, POST, HEAD, -OPTIONS",                                                                
              SERVICEORDER = "URI,EXT",                                                                            
              SSLNAME = "ssl",                                                                                     
              SSLFLAG = Y,                                                                                         
              LOGGING = "acc_PMS",                                                                                 
              ERRORLOG = "err_PMS"                                                                                 
                                                                                                                   
v_PRP         DOCROOT="/app/clip/webdoc",                                                                          
              HOSTNAME = "clip_pms.kdb.co.kr",                                                                            
              PORT = "20081",                                                                                      
              ERRORDOCUMENT = "400,401,403,404,405,500,503",                                                       
                          METHOD = "GET, POST, HEAD, -OPTIONS",                                                    
              SERVICEORDER = "URI,EXT",                                                                            
              LOGGING = "acc_PRP",                                                                                 
              ERRORLOG = "err_PRP"                                                                                 
                                                                                                                   
v_PRP_S       DOCROOT="/app/clip/webdoc",                                                                          
              HOSTNAME = "clip_pms.kdb.co.kr",                                                                            
              PORT = "20443",                                                                                      
              ERRORDOCUMENT = "400,401,403,404,405,500,503",                                                       
              METHOD = "GET, POST, HEAD, -OPTIONS",                                                                
              SERVICEORDER = "URI,EXT",                                                                            
              SSLNAME = "ssl",                                                                                     
              SSLFLAG = Y,                                                                                         
              LOGGING = "acc_PRP",                                                                                 
              ERRORLOG = "err_PRP"                                                                                 
                                                                                                                   
v_ITG         DOCROOT="/app/imxpert/webdoc",
              HOSTNAME = "itsm.kdb.co.kr",
              HOSTALIAS = "itsm.kdb.co.kr",
              PORT = "20082",
              ERRORDOCUMENT = "400,401,403,404,405,500,503",
              METHOD = "GET, POST, HEAD, -OPTIONS",
              SERVICEORDER = "URI,EXT",
              LOGGING = "acc_ITG",
              TimeOut = 308,
              ERRORLOG = "err_ITG"

v_ITG_S       DOCROOT="/app/imxpert/webdoc",
              HOSTNAME = "ditsm.kdb.co.kr",
              HOSTALIAS = "ditsm.kdb.co.kr",
              PORT = "20443",
              ERRORDOCUMENT = "400,401,403,404,405,500,503",
              METHOD = "GET, POST, HEAD, -OPTIONS",
              SERVICEORDER = "URI,EXT",
              SSLNAME = "ssl",
              SSLFLAG = Y,
              LOGGING = "acc_ITG",
              TimeOut = 308,
              ERRORLOG = "err_ITG"

### PMS real #####                                                                                                 
v_PMP_S       DOCROOT="/app/wisepms/webapp/wisepms",                                                               
              HOSTNAME = "pms.kdb.co.kr",                                                                         
              HOSTALIAS = "pms.kdb.co.kr",                                                                        
              PORT = "20443",                                                                                      
              ERRORDOCUMENT = "400,401,403,404,405,500,503",                                                       
              METHOD = "GET, POST, HEAD, -OPTIONS",                                                                
              SERVICEORDER = "URI,EXT",                                                                            
              SSLNAME = "ssl",                                                                                     
              SSLFLAG = Y,                                                                                         
              LOGGING = "acc_PMP",                                                                                 
                                                                                                                   
*SSL                                                                                                               
ssl           CertificateFile="/sw/webtob/ssl/newreq.pem",                                                         
              CertificateKeyFile="/sw/webtob/ssl/newreq.pem",                                                      
              CACertificateFile="/sw/webtob/ssl/ThawteDigiCert-Newchain.pem",                                   
              Protocols = "-SSLv3, TLSv1, TLSv1.1, TLSv1.2",                                                       
              RequiredCiphers = "HIGH:MEDIUM:!SSLv2:!PSK:!SRP:!ADH:!AECDH:!EXP:!RC4:!IDEA:!3DES"                   
                                                                                                                   
*SVRGROUP                                                                                                          
htmlg         SVRTYPE = HTML                                                                                       
jsvg_PMS      SVRTYPE = JSV, VHOSTNAME = "v_PMS, v_PMS_S"                                                          
jsvg_PRP      SVRTYPE = JSV, VHOSTNAME = "v_PRP, v_PRP_S"                                                          
jsvg_ITG      SVRTYPE = JSV, VHOSTNAME = "v_ITG, v_ITG_S"                                                          
jsvg_PMP      SVRTYPE = JSV, VHOSTNAME = "v_PMP, v_PMP_S"                                                                 
                                                                                                                   
*SERVER                                                                                                            
PMS           SVGNAME = jsvg_PMS,   MinProc = 100, MaxProc = 100, RequestLevelPing=Y                                 
PRP           SVGNAME = jsvg_PRP,   MinProc = 60, MaxProc = 60, RequestLevelPing=Y                                 
ITG           SVGNAME = jsvg_ITG,   MinProc = 60, MaxProc = 60, RequestLevelPing=Y                                 
PMP           SVGNAME = jsvg_PMP,   MinProc = 100, MaxProc = 100, RequestLevelPing=Y                                 
                                                                                                                   
*URI                                                                                                               
uri_PMS_JSV   Uri = "/",               Svrtype = JSV,  SVRNAME = "PMS", VHOSTNAME ="v_PMS, v_PMS_S"                
uri_PRP_JSV   Uri = "/ClipReport4/",   Svrtype = JSV,  SVRNAME = "PRP", VHOSTNAME ="v_PRP, v_PRP_S", GOTOEXT=Y     
uri_ITG_JSV   Uri = "/",               Svrtype = JSV,  SVRNAME = "ITG", VHOSTNAME ="v_ITG, v_ITG_S"                
uri_PMP_JSV   Uri = "/",               Svrtype = JSV,  SVRNAME = "PMP", VHOSTNAME ="v_PMP_S"                       
                                                                                                                   
                                                                                                                   
*ALIAS                                                                                                             
a_clip        URI = "/ClipReport4/", RealPath = "/app/clip/webdoc/", VHOSTNAME="v_PRP, v_PRP_S"                    
                                                                                                                   
*LOGGING                                                                                                           
syslog        Format = "SYSLOG",  FileName = "/log/webtob/system/system.log_%M%%D%%Y%", Option = "sync"            
acc_node      Format = "DEFAULT", FileName = "/log/webtob/node/access.log_%M%%D%%Y%",   Option = "sync, env=!image"
err_node      Format = "ERROR",   FileName = "/log/webtob/node/error.log_%M%%D%%Y%",    Option = "sync, env=!image"
acc_PMS       Format = "DEFAULT", FileName = "/log/webtob/PMS/access.log_%M%%D%%Y%",    Option = "sync, env=!image"
err_PMS       Format = "ERROR",   FileName = "/log/webtob/PMS/error.log_%M%%D%%Y%",     Option = "sync, env=!image"
acc_PRP       Format = "DEFAULT", FileName = "/log/webtob/PRP/access.log_%M%%D%%Y%",    Option = "sync, env=!image"
err_PRP       Format = "ERROR",   FileName = "/log/webtob/PRP/error.log_%M%%D%%Y%",     Option = "sync, env=!image"
acc_ITG       Format = "DEFAULT", FileName = "/log/webtob/ITG/access.log_%M%%D%%Y%",    Option = "sync, env=!image"
err_ITG       Format = "ERROR",   FileName = "/log/webtob/ITG/error.log_%M%%D%%Y%",     Option = "sync, env=!image"
acc_PMP       Format = "DEFAULT", FileName = "/log/webtob/PMP/access.log_%M%%D%%Y%",    Option = "sync, env=!image"
err_PMP       Format = "ERROR",   FileName = "/log/webtob/PMP/error.log_%M%%D%%Y%",     Option = "sync, env=!image"
                                                                                                                   
*ERRORDOCUMENT                                                                                                     
400           status = 400, url = "/error.html"                                                                    
401           status = 401, url = "/error.html"                                                                    
403           status = 403, url = "/error.html"                                                                    
404           status = 404, url = "/error.html"                                                                    
405           status = 405, url = "/error.html"                                                                    
500           status = 500, url = "/error.html"                                                                    
503           status = 503, url = "/error.html"                                                                    
                                                                                                                   
*EXT                                                                                                               
htm           MimeType = "text/html",                      SVRTYPE = HTML
html          MimeType = "text/html",                      SVRTYPE = HTML
jsp           MimeType = "application/jsp",                SVRTYPE = JSV,  Options = "Unset"
do            MimeType = "application/do",                 SVRTYPE = JSV,  Options = "Unset"
bmp           MimeType = "image/bmp",                      SVRTYPE = HTML
cab           MimeType = "application/x-msdownload",       SVRTYPE = HTML
css           MimeType = "text/css",                       SVRTYPE = HTML
doc           MimeType = "application/msword",             SVRTYPE = HTML
dot           MimeType = "application/msword",             SVRTYPE = HTML
exe           MimeType = "application/octet-stream",       SVRTYPE = HTML
gif           MimeType = "image/gif",                      SVRTYPE = HTML
png           MimeType = "image/png",                      SVRTYPE = HTML
hlp           MimeType = "application/winhlp",             SVRTYPE = HTML
hta           MimeType = "application/hta",                SVRTYPE = HTML
htc           MimeType = "text/x-component",               SVRTYPE = HTML
ico           MimeType = "image/x-icon",                   SVRTYPE = HTML
jpg           MimeType = "image/jpeg",                     SVRTYPE = HTML
js            MimeType = "application/x-javascript",       SVRTYPE = HTML
pdf           MimeType = "application/pdf",                SVRTYPE = HTML
pps           MimeType = "application/vnd.ms-powerpoint",  SVRTYPE = HTML
ppt           MimeType = "application/vnd.ms-powerpoint",  SVRTYPE = HTML
ps            MimeType = "application/postscript",         SVRTYPE = HTML
swf           MimeType = "application/x-shockwave-flash",  SVRTYPE = HTML
txt           MimeType = "text/plain",                     SVRTYPE = HTML
xla           MimeType = "application/vnd.ms-excel",       SVRTYPE = HTML
xlc           MimeType = "application/vnd.ms-excel",       SVRTYPE = HTML
xsl           MimeType = "text/html",                      SVRTYPE = HTML
zip           MimeType = "application/zip",                SVRTYPE = HTML
ocx           MimeType = "application/x-pe-win32-x86",     SVRTYPE = HTML
xls           MimeType = "application/vnd.ms-excel",       SVRTYPE = HTML
xlsx          MimeType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",         SVRTYPE = HTML
docx          MimeType = "application/vnd.openxmlformats-officedocument.wordprocessingml.document",   SVRTYPE = HTML
pptx          MimeType = "application/vnd.openxmlformats-officedocument.presentationml.presentation", SVRTYPE = HTML
#### clipReport ADD ###
svg           MimeType = "image/svg+xml",                  SVRTYPE = HTML
ttf           MimeType = "application/x-font-ttf ",        SVRTYPE = HTML
woff          MimeType = "application/x-font-woff ",       SVRTYPE = HTML
eot           MimeType = "application/vnd.ms-fontobject",  SVRTYPE = HTML
