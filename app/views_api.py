from . import appbuilder, app
from flask import jsonify, request
from flask_appbuilder import Model
from collections.abc import Iterable
from flask_appbuilder.api import BaseApi, expose, safe, rison, protect
from .sqls_monitor import getGridConfig, getAllFromTable, getModelInfo, getAllTables
import enum
import sys
from datetime import datetime, time
import json
import re
#import time

class ModelSpecView(BaseApi):

    resource_name = 'model'

    @expose('/column_all/<table_column>', methods=['GET'])
    @protect(allow_browser_login=True)
    def colvalues_all(self, table_column):

        table_name, column_name = table_column.split('.')

        if request.args:
            tmp = request.args.get('condition')
            condition = [json.loads(tmp)]
        else:
            condition = None

        col_recs, _ = getAllFromTable(table_name, column_name, condition=condition, distinct=False)

        col_list = []
        if col_recs:
            [ col_list.append({'pk':r[1],'value':r[0]}) for r in col_recs ]        

        return jsonify({'list':col_list})

    @expose('/column_distinct/<table_column>', methods=['GET'])
    @protect(allow_browser_login=True)
    def colvalues_distinct(self, table_column):

        table_name, column_name = table_column.split('.')

        col_recs, _ = getAllFromTable(table_name, column_name, distinct=True)

        col_list = []
        if col_recs:
            [ col_list.append({'pk':r[0],'value':r[0]}) for r in col_recs ]        

        return jsonify({'list':col_list})

    @expose('/modelinfo/<table>', methods=['GET'])
    @protect(allow_browser_login=True)
    def modelinfo(self, table):

        dic = getModelInfo(table)

        return jsonify({'dict':dic})

    @expose('/tables', methods=['GET'])
    @protect(allow_browser_login=True)
    def tables(self):

        tables = getAllTables()

        print(tables)

        return jsonify({'list':tables})

class GridView(BaseApi):

    #route_base = '/grid'
    resource_name = 'grid'

    def getLastValues(self, orig_v, seperator=',', condition=None):

        str_v = ''

        if isinstance (orig_v, enum.Enum):
            str_v = self.__meetCondition(orig_v.value, condition)
        elif isinstance(orig_v, Model):
            str_v = self.__meetCondition(str(orig_v), condition)
        elif isinstance (orig_v, time):
            str_v = orig_v.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(orig_v, list):
            tmp = [ self.__meetCondition(str(v), condition) for v in orig_v]
            str_v = seperator.join(tmp) if tmp else ''
        elif orig_v:
            str_v = self.__meetCondition(str(orig_v), condition)

        return str_v

    def __meetCondition(self, value, condition):

        if condition:
            operator, operand = condition

            condition_map = {
                            'like':operand in value
                            , 'nlike':operand not in value
                            , 'eql':operand==value
                            , 'neql':operand!=value
                            }

            return value if condition_map[operator] else ''
        else:
            return value

    def __getColName(self, text):

        p0 = r'\([^)]*\)'

        return re.sub(p0, repl='',string=text)

    def __getCondition(self, text):

        p1 = r'\(([^)]+)'

        bracket = re.findall(p1, text)
        if bracket:
            cond, value = bracket[0].split('__')
            return cond, value
        else:
            return None

    def getColValues(self, rec, colName, seperator=','):

        val = ''

        this_col = colName.split('.')[0]
        this_colname = self.__getColName(this_col)
        this_condition = self.__getCondition(this_col)

        first_item = getattr(rec, this_colname)
        next_colName = '.'.join(colName.split('.')[1:])

        #print('Hennry COL : ',colName,':', first_item,':', next_colName)
        if not next_colName:
            val = self.getLastValues(first_item, seperator=seperator, condition=this_condition)
        elif isinstance(first_item, list):
            for v in first_item:
                val = val + (seperator if val else '') + self.getColValues(v, next_colName, seperator=seperator)
        else:
            val = self.getColValues(first_item, next_colName, seperator)

        if seperator in val:
            val = val.split(seperator)
            val = list(filter(None,set(val)))
            val.sort()
            val = seperator.join(val)

        return val

    @expose('/gridlist', methods=['GET'])
    @protect(allow_browser_login=True)
    def gridlist(self):

        recs = getGridConfig()

        list = []
        if recs:
            [ list.append({'pk':r.grid_key,'value':r.title+'('+ r.grid_key +')'}) for r in recs ]

        return jsonify({'list':list})

    @expose('/table/<param>', methods=['GET'])
    @protect(allow_browser_login=True)
    def table_view2(self, param):

        cmd = request.args.get('cmd')

        rec = getGridConfig(param)

        if not rec:
            return jsonify({'msg':'Param is not found'}), 404    

        table_name = rec.table_name
        columns    = rec.columns.split(',')
        header     = rec.headers.split(',') if rec.headers else ''
        widths     = rec.widths.split(',') if rec.widths else ''
        tmp        = rec.default_condition if rec.default_condition else ''
        tmp        = '{"conditions":[' + tmp + ']}'
        conditions = json.loads(tmp)
        seperator  = rec.seperator if rec.seperator else ','
        #cond_list = []
        #for c in conditions:
        #    cond_list.append(dict(
        #        name = c
        #       ,operations=self.condtype_map[getColType(table_name, c)])
        #       )
        title      = rec.title
        file_name  = rec.file_name
        page_dblclick = rec.page_dblclick if rec.rows_per_page else ''
        rows_per_page = rec.rows_per_page if rec.rows_per_page else 25

        if cmd == 'nodata':
            #return jsonify({'list':[], 'columns':columns, 'labels':header, 'widths':widths, 'title':title, 'file_name':file_name, 'rows_per_page':rows_per_page, 'page_dblclick':page_dblclick, 'conditions':cond_list}), 200
            return jsonify({'list':[], 'columns':columns, 'labels':header, 'widths':widths, 'title':title, 'file_name':file_name, 'rows_per_page':rows_per_page, 'page_dblclick':page_dblclick}), 200

        try:

            condition = []
            join_table_name = ''
            nm_column_name = ''
            join_conditions = {}

            for cond in conditions['conditions']:

                if '.' in cond['column']:

                    val2 = cond['column'].split('.')

                    if len(val2)>2:
                        return jsonify({'msg':'Column:'+cond['column']+' is invalid.'}), 500

                    join_table_name = val2[0]
                    v_dict = dict(
                             operator = cond['operator']
                            ,column   = val2[1]
                            ,value    = cond['value']
                            ) 
                    if join_conditions.get(join_table_name):
                        join_conditions[join_table_name].append(v_dict)
                    else:
                        join_conditions[join_table_name] = [v_dict]

                else:
                    condition.append(cond)

            for arg in request.args:

                val = arg.split('__')

                if len(val)<2:
                    continue

                if '.' in val[1]:
                    val2 = val[1].split('.')

                    if len(val2)>2:
                        return jsonify({'msg':'Column:'+val[1]+' is invalid.'}), 500

                    join_table_name = val2[0]
                    v_dict = dict(
                             operator = val[0]
                            ,column   = val2[1]
                            ,value    = request.args[arg]
                            ) 
                    if join_conditions.get(join_table_name):
                        join_conditions[join_table_name].append(v_dict)
                    else:
                        join_conditions[join_table_name] = [v_dict]
                else:
                    condition.append(
                        dict(
                        operator = val[0]
                        ,column   = val[1]
                        ,value    = request.args[arg])
                    )

            recs, _ = getAllFromTable(table_name, condition=condition, join_conditions=join_conditions)

        except KeyError as e:
            return jsonify({'msg':'Table:'+table_name+' dose not exist'}), 500

        grid_list = []
        
        try:

            if recs:
                for r in recs:
                
                    grid_row = {}

                    for col in columns:

                        if col.startswith('t__') and callable(getattr(r, col)):
                            grid_row[col] = getattr(r, col)()
                        else:
                            grid_row[col] = self.getColValues(r, col, seperator)

                    grid_row['id'] = r.id
                    grid_list.append(grid_row)

        except AttributeError as e:
            excType, excValue, traceback = sys.exc_info()
            print('AttributeError Error : ', excType, excValue, traceback)
                
            return jsonify({'msg':rec.columns+' is not valid.'}), 500

        #return jsonify({'list':grid_list, 'columns':columns, 'labels':header, 'widths':widths, 'title':title, 'file_name':file_name, 'rows_per_page':rows_per_page, 'page_dblclick':page_dblclick, 'conditions':cond_list}), 200
        return jsonify({'list':grid_list, 'columns':columns, 'labels':header, 'widths':widths, 'title':title, 'file_name':file_name, 'rows_per_page':rows_per_page, 'page_dblclick':page_dblclick}), 200


appbuilder.add_api(ModelSpecView)
appbuilder.add_api(GridView)