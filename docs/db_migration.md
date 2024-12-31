Step-by-Step flask db migration

#### 1. mwm-app container shell 접속
```
docker exec -it mwm-app sh
```
#### 2. kill gunicorn processes
```
pkill gunicorn
```
#### 3. create migration file
```
flask db migrate
```
#### 4. apply migration file
```
flask db upgrade
```
