FROM mwm-base

ENV FAB_HOME=/usr/local/lib/python3.12/site-packages/flask_appbuilder
ENV FAB_STATIC_DIR=${FAB_HOME}/static/appbuilder
ENV FAB_TEMPLATES_DIR=${FAB_HOME}/templates/appbuilder

# datetimepicker import 설정
RUN sed -i '/bootstrap-datepicker3.min.css/a \
<link href="{{url_for(\x27appbuilder.static\x27,filename=\x27css/bootstrap-datepicker/bootstrap-datetimepicker.min.css\x27)}}" rel="stylesheet">' \
${FAB_TEMPLATES_DIR}/init.html

RUN sed -i '/bootstrap-datepicker.min.js/a \
<script src="{{url_for(\x27appbuilder.static\x27,filename=\x27js/bootstrap-datepicker/moment.min.js\x27)}}" nonce="{{baselib.get_nonce()}}"></script>\n\
<script src="{{url_for(\x27appbuilder.static\x27,filename=\x27js/bootstrap-datepicker/bootstrap-datetimepicker.min.js\x27)}}" nonce="{{baselib.get_nonce()}}"></script>' \
${FAB_TEMPLATES_DIR}/init.html

# DateTimePickerWidget 의 설정된 picker 이름 변경
RUN sed -i '/\$(\x27.appbuilder_datetime\x27).datepicker({/,/});/c\
$(\x27.appbuilder_datetime\x27).datetimepicker({ \
    format: \x27YYYY-MM-DD HH:mm:ss\x27 \
});' ${FAB_STATIC_DIR}/js/ab.js

RUN sed -i 's/data-provide="datepicker" id="datetimepicker"/data-provide="datetimepicker" id="datetimepicker"/g' \
${FAB_HOME}/fieldwidgets.py

# datetimepicker js copy
COPY ./files_into_image/bootstrap-datetimepicker.min.css ${FAB_STATIC_DIR}/css/bootstrap-datepicker/
COPY ./files_into_image/bootstrap-datetimepicker.min.js ${FAB_STATIC_DIR}/js/bootstrap-datepicker/
COPY ./files_into_image/moment.min.js ${FAB_STATIC_DIR}/js/bootstrap-datepicker/

# Set working directory (should match the base image's WORKDIR)
WORKDIR /app

# Copy the source code
COPY app app
COPY config.py config.py
COPY run.py run.py

# Copy Gunicorn configuration file
COPY gunicorn_config.py gunicorn_config.py

# Expose the port the application will run on
EXPOSE 8000

# Use Gunicorn to run the application
#CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]

# Supervisor 설정 복사
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Supervisor를 ENTRYPOINT로 설정
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]