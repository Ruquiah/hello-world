@app.route('/cached_reports',method='GET')
def get_cached_report():
    
    Generates xls report for assets in cache.
    Input ex: { /cached_reports --> Generates a xlsx report on all cached assets}
          ex: {"from_date":" ","to_date":" " --> Generates a xlsx report on cached assets within the range specified}
    Output Returns xls static file.
            
    try:

        info = json.loads(bottle.request.query.s) if bottle.request.query.s else {}
        logger.debug("[get_cached_report] Input info is: {}".format(info))

        timestamp  = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename   = "cache_report" + timestamp + '.xlsx'
        if os.name == "posix":
            xls_file_path = '/opt/HSM3/Reports'
        else:
            xls_file_path = 'C:\\Karthavya\\HSM3\\Reports'

        if not os.path.exists(xls_file_path):
            os.mkdir(xls_file_path)
        file_path          = os.path.join(xls_file_path,filename)
        xls_heading_list   = ["FileName","FileSize","Created Time","PoolID","ArchivedLocations"]
        dict_keys          = ["file_name","size","created_time","pool_ids","archived_locations"]
        cached_assets_list = []
    
        if info.get("from_date") and info.get("to_date"):
            db_query      = {"created_time": {"$gte": info["from_date"], "$lte": info["to_date"]}}
            cached_assets = list(db.cached.find(db_query))
        else:
            cached_assets = list(db.cached.find())

        for asset in cached_assets:
            try:
                asset_info                 = {}
                asset_info["file_name"]    = asset["file_name"]
                if asset.get("size"):
                    filesize               = asset["size"]
                    asset_info["size"]     = humanize.naturalsize(filesize)
                else:
                    filesize               = asset["file_size"]
                    asset_info["size"]     = humanize.naturalsize(filesize)
                asset_info["created_time"] = str(asset["created_time"])

                if isinstance(asset["pool_ids"],list):
                    pool     = ""
                    pool_ids = []
                    for ids in asset["pool_ids"]:
                        pool += ids + ', '
                    pool_ids.append(pool)
                    asset_info["pool_ids"] = pool_ids
                else:
                    asset_info["pool_ids"] = asset["pool_ids"]
                
                location      = " "
                location_list = []
                archived_locations = list(db.archive.find({"archive_id":asset["archive_id"]},{"_id":0,"archived_locations":1}))
                logger.debug("Archived locations {}".format(archived_locations))
                for device in archived_locations:
                    for dev_ in device["archived_locations"]:
                        archive_type = dev_.get("archive_type")
                        container_id = dev_.get("container_id")
                        location    += archive_type + ':' +container_id+ ', '
                location_list.append(location)
                asset_info["archived_locations"] = location_list
            except Exception as ex:
                logger.debug("[get_cached_report] Exception obtained. Reason --> {}".format(ex))  
            cached_assets_list.append(asset_info)
        print(cached_assets_list)
        logger.debug("[get_cached_report] Number of assets found is: {}".format(len(cached_assets_list)))
        if not info.get("download") :
            return {"cached_assets" : utils.json_friendly(cached_assets_list)}
        if cached_assets_list:
            xls_file = utils.write_content_to_xls_file(cached_assets_list, xls_heading_list, dict_keys, file_path)
            if not xls_file:
                bottle.abort(500, json.dumps({'errors':["Not able to create xls file"]}))
            utils.delete_xls_reports(xls_file_path)
            return static_file(filename, xls_file_path, download=filename)  

    except Exception as e:
        logger.debug("[get_cached_report] Exception obtained. Reason --> {}".format(e))

@app.route('/containers_reports',method='GET')
def get_containers_report():
    """
    Generates xls file for the assets in given container
    Input  ex: { /containers_reports } --> Generates xls report on all containers.
           ex: {"primary_containers": True} --> Generates xls report for primary containers.
           ex: {"backup_containers": True} --> Generates xls report for backup containers.
           ex: {"containers_list" : [" "," "," "...]} --> Generates xls report for given list of container_ids.
    Output Returns xls static file. 
    """
    try:

        info = json.loads(bottle.request.query.s) if bottle.request.query.s else {}
        logger.debug("[get_containers_report] Input info is: {}".format(info))

        timestamp  = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename   = "containers_report" + timestamp + '.xlsx'
        if os.name == "posix":
            xls_file_path = '/opt/HSM3/Reports'
        else:
            xls_file_path = 'C:\\Karthavya\\HSM3\\Reports'

        if not os.path.exists(xls_file_path):
            os.mkdir(xls_file_path)
        file_path             = os.path.join(xls_file_path,filename)
        xls_heading_list      = ["FileName","FileSize","Created Time","PoolID","Archived Location","Label"]
        dict_keys             = ["file_name","size","created_time","pool_id","archived_locations","label"]
        container_assets_list = []
        container_list        = []

        if info.get("primary_containers"):
            container_assets = list(db.archive.find({"archived_locations":{"$elemMatch":{"archive_type":"primary"}}}))
        if info.get("backup_containers"):
            container_assets = list(db.archive.find({"archived_locations":{"$elemMatch":{"archive_type":"backup"}}}))
        if info.get("containers_list"):
            if not isinstance(info["containers_list"],list):
                raise Exception ("Container ids should be a list parameter.")

            for container in info["containers_list"]:
                if db.inventory.find_one({"container_id":container}):
                    container_list.append(container)
                else:
                    print("Not a valid Container ID")
            container_assets = list(db.archive.find({"archived_locations":{"$elemMatch":{"container_id":{"$in":container_list}}}}))
        else:
            container_assets = list(db.archive.find())

        for asset in container_assets:
            try:
                asset_info                 = {}
                asset_info["file_name"]    = asset["file_name"]

                filesize                   = asset["file_size"]
                asset_info["size"]         = humanize.naturalsize(filesize)

                asset_info["created_time"] = str(asset["created_time"])
                pool                       = ""
                pool_ids_list              = []
                for device in asset["archived_locations"]:                    
                    if isinstance(device["pool_id"],list):                        
                        for dev_ in device["pool_id"]:
                            pool += dev_ + ', '
                        pool_ids_list.append(pool)
                        pool = ""
                    else:
                        pool_ids_list.append(device["pool_id"])
                asset_info["pool_id"] = pool_ids_list

                location            = ""
                location_list       = []
                container_ids_list  = []
                for device in asset["archived_locations"]:                    
                    archive_type    = device.get("archive_type")
                    container_id    = device.get("container_id")
                    location       += archive_type + ':' +container_id+ ', '
                    container_ids_list.append(container_id)
                location_list.append(location)
                asset_info["archived_locations"] = location_list

                labels_          = ""
                label_value      = []
                for id_ in container_ids_list:
                    all_labels   = (db.inventory.find_one({"container_id":id_},{"label":1}))
                    if all_labels is not None:
                        value    = all_labels.get("label")
                        labels_ += value + ', '
                label_value.append(labels_)
                asset_info["label"] = label_value

            except Exception as ex:
                logger.debug('[get_containers_report] Exception obtained. Reason :: {}'.format(ex))
            container_assets_list.append(asset_info)
        print(container_assets_list)
        logger.debug("The number of assets found {}".format(len(container_assets_list)))
        if not info.get("download") :
            return {"container_assets" : utils.json_friendly(container_assets_list)}
        if container_assets_list:
            xls_file = utils.write_content_to_xls_file(container_assets_list, xls_heading_list, dict_keys, file_path)
            if not xls_file:
                bottle.abort(500, json.dumps({'errors':["Not able to create xls file"]}))
            utils.delete_xls_reports(xls_file_path)
            return static_file(filename, xls_file_path, download=filename)

    except Exception as ex:
        logger.debug("[containers_report] Exception obtained. Reason :: {}".format(ex))

@app.route('/storage_reports',method='GET')
def get_storage_report():
    """
    Generates xls file for the assets in given container
    Input  ex: { /storage_reports } --> Generates xls report on all containers and bins.
           ex: {"bins": True, "bin_id":["","",""] or "bin_type":" "} --> Generates xls report for bins with specified parameters.
           ex: {"containers": True, "container_id":["","",""] or "type":" " 
                or "primary_containers": True or "backup_containers": True} --> Generates xls report for containers with specified parameters.
    Output Returns xls static file.
    """
    try:

        info = json.loads(bottle.request.query.s) if bottle.request.query.s else {}
        logger.debug("[get_storage_report] Input info is: {}".format(info))

        timestamp  = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename   = "storage_report" + timestamp + '.xlsx'
        if os.name == "posix":
            xls_file_path = '/opt/HSM3/Reports'
        else:
            xls_file_path = 'C:\\Karthavya\\HSM3\\Reports'

        if not os.path.exists(xls_file_path):
            os.mkdir(xls_file_path)
        file_path      = os.path.join(xls_file_path,filename)
        dict_keys      = ["id","total_space","free_space","used_space","number_of_archived_files","enable","read_only"]
        container_list = []
        bin_ids_list   = []
        storage_list   = []
        
        if info.get("containers"):
            if info.get("container_ids"):
                if not isinstance(info["container_ids"],list):
                    raise Exception ("Container ids should be a list parameter.")
                for container in info["container_ids"]:
                    if db.inventory.find_one({"container_id":container}):
                        container_list.append(container)
                    else:
                        print ("Not a valid Container ID")
                container_assets_for_storage_report     = list(db.inventory.find({"container_id":{"$in":container_list}}))
    
            if info.get("type"):
                if db.inventory.find_one({"type":info["type"]}):
                    container_assets_for_storage_report = list(db.inventory.find({"type":info["type"]}))
                else:
                    raise Exception ("Container Type not valid")

            if info.get("primary_containers"):
                container_assets_for_storage_report     = list(db.inventory.find())

            if info.get("backup_containers"):
                backup_cont_list                        = list(db.inventory.find({"mirror_containers":{"$exists":True}},{"_id":0,"mirror_containers":1}))
                backup = []
                for cont_ in backup_cont_list:
                    backup.extend(cont_.get("mirror_containers"))
                container_assets_for_storage_report     = list(db.inventory.find({"container_id":{"$in":backup}}))
            
            xls_heading_list = ["Container ID","Total Space","Free Space ","Used Space","Number of archived files","Enable","Read Only"]
        
        if info.get("bins"):
            if info.get("bin_id"):
                if not isinstance(info["bin_id"],list):
                    raise Exception ("Bin ids should be a list parameter.")
                for bin_ in info["bin_id"]:
                    if db.bins.find_one({"_id":bin_}):
                        bin_ids_list.append(bin_)
                    else:
                        print ("Bin_id not valid")
                container_assets_for_storage_report     = list(db.bins.find({"_id":{"$in":bin_ids_list}}))
    
            if info.get("bin_type"):
                if db.bins.find_one({"bin_type":info["bin_type"]}):
                    container_assets_for_storage_report = list(db.bins.find({"bin_type":info["bin_type"]}))
                else:
                    raise Exception ("Bin_type not valid")

            xls_heading_list  = ["Bin ID","Total Space","Free Space ","Used Space","Number of archived files","Enable","Read Only"]

        else:
            container_assets1 = list(db.inventory.find())
            container_assets2 = list(db.bins.find())
            container_assets_for_storage_report = container_assets1 + container_assets2 
            xls_heading_list  = ["ID","Total Space","Free Space ","Used Space","Number of archived files","Enable","Read Only"]   

        for asset in container_assets_for_storage_report:
            try:
                asset_info  = {}

                t_space     = asset.get("total_space"," ")
                if t_space != " ": 
                    asset_info["total_space"] = humanize.naturalsize(t_space)
                else:
                    asset_info["total_space"] = t_space
                f_space      = asset.get("free_space"," ")
                if f_space  != " ":
                    asset_info["free_space"] = humanize.naturalsize(f_space)
                else:
                    asset_info["free_space"]   = f_space
                if t_space != " " and f_space != " ":
                    u_space = t_space - f_space
                    asset_info["used_space"] = humanize.naturalsize(u_space)
                else:
                    asset_info["used_space"] = " "

                if asset.get("container_id"):
                    asset_info["id"] = asset["container_id"]
                elif asset.get("_id"):
                    asset_info["id"] = asset["_id"]
                
                asset_info["number_of_archived_files"] = asset.get("number_of_archive_file"," ")
                asset_info["enable"]                   = asset.get("enable"," ")
                asset_info["read_only"]                = asset.get("read_only"," ")
            except Exception as ex:
                logger.debug('[get_storage_report] Exception obtained. Reason :: {}'.format(ex))
            storage_list.append(asset_info)
        print(storage_list)
        logger.debug("The number of assets found {}".format(len(storage_list)))
        if not info.get("download") :
            return {"container_assets_for_storage" : utils.json_friendly(storage_list)}
        if storage_list:
            xls_file = utils.write_content_to_xls_file(storage_list, xls_heading_list, dict_keys, file_path)
            if not xls_file:
                bottle.abort(500, json.dumps({'errors':["Not able to create xls file"]}))
            utils.delete_xls_reports(xls_file_path)
            return static_file(filename, xls_file_path, download=filename)
    except Exception as ex:
        logger.debug("[storage_report] Exception obtained. Reason :: {}".format(ex))

@app.route('/user_reports',method='GET')
def get_user_report():
    """
    Generates xls file for the assets in given container
    Input  ex: { /user_reports } --> Generates xls report on all users.
           ex: {"from_date":" ", "to_date":" "} --> Generates xls report for all users activity within the date specified.
           ex: {"command": " " } --> Generates xls report of all users activity for that command.
    Output Returns xls static file.
    """
    try:

        info = json.loads(bottle.request.query.s) if bottle.request.query.s else {}
        logger.debug("[get_user_report] Input info is: {}".format(info))

        timestamp  = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename   = "user_report" + timestamp + '.xlsx'
        if os.name == "posix":
            xls_file_path = '/opt/HSM3/Reports'
        else:
            xls_file_path = 'C:\\Karthavya\\HSM3\\Reports'

        if not os.path.exists(xls_file_path):
            os.mkdir(xls_file_path)
        file_path            = os.path.join(xls_file_path,filename)
        xls_heading_list     = ["User Name","Archive To Cache ","Archive To Disk","Archive To Container","Retrieve"]
        dict_keys            = ["username","ArchiveToCache","ArchiveToDisk","ArchiveToContainer","Retrieve"]        
        users_list           = []
        commands             = [constants.COMMAND_ARCHIVE_TO_CACHE, constants.COMMAND_ARCHIVE_TO_CONTAINER, constants.COMMAND_ARCHIVE_TO_DISK,constants.COMMAND_RETRIEVE]
        id_from_users_collec = list(db.users.find({},{"_id":1}))
        extracted_ids        = []
        for id_ in id_from_users_collec:
            user_id = str(id_.get("_id"))
            extracted_ids.append(user_id)

        if info.get("from_date") and info.get("to_date"):
            for each_id in extracted_ids:
                try:
                    asset_info           = {}                   
                    user_completed_jobs  = list(db.jobs.aggregate([{"$match":{"user_id": each_id,"status":constants.JOB_STATUS_COMPLETED,
                                                                    "created_datetime":{"$gte":info["from_date"],"$lte":info["to_date"]}}},
                                                                    {"$group":{"_id":"$command","count": {"$sum":1}}
                                        }]))
                    user_failed_jobs     = list(db.jobs.aggregate([{"$match":{"user_id": each_id,"status":constants.JOB_STATUS_FAILED,
                                                                    "created_datetime":{"$gte":info["from_date"],"$lte":info["to_date"]}}},
                                                                    {"$group":{"_id":"$command","count": {"$sum":1}}
                                        }]))
                    completed_count_value = {data["_id"]: data["count"] for data in user_completed_jobs}
                    failed_count_value    = {data["_id"]: data["count"] for data in user_failed_jobs}
    
                    for command in commands:
                        temp = ""
                        if completed_count_value.get(command):
                            temp += str(completed_count_value[command]) + "(completed), "
                        else:
                            temp += str(0) + "(completed), "
                        
                        if failed_count_value.get(command):
                            temp += str(failed_count_value[command]) + "(failed)"
                        else:
                            temp += str(0) + "(failed)"
                    
                        asset_info[command] = temp                                          
                        print (asset_info[command])
                    username                = db.users.find_one({"_id":ObjectId(each_id)},{"_id":0,"username":1})
                    asset_info["username"]  = username.get("username")
                except Exception as ex:
                    logger.debug('[get_user_report] Exception obtained. Reason:: {}'.format(ex))    
                users_list.append(asset_info)
            print(users_list)
            logger.debug("The number of assets found {}".format(len(users_list)))

        if info.get("command"):
            if db.jobs.find_one({"command":info["command"]}):

                xls_heading_list = ["User Name",info["command"]]
                dict_keys        = ["username",info["command"]]        
                for each_id in extracted_ids:
                    try:
                        asset_info          = {}
                        user_completed_jobs = db.jobs.find({"user_id": each_id,"status":constants.JOB_STATUS_COMPLETED,
                                                            "command":info["command"]}).count()
                                        
                        user_failed_jobs    = db.jobs.find({"user_id": each_id,"status":constants.JOB_STATUS_FAILED,
                                                            "command":info["command"]}).count()
                                        
                        temp                        = ""
                        temp                       += str(user_completed_jobs) + "(completed), " + str(user_failed_jobs) + "(failed)"
                        asset_info[info["command"]] = temp
                        username                    = db.users.find_one({"_id":ObjectId(each_id)},{"_id":0,"username":1})
                        asset_info["username"]      = username.get("username")

                    except Exception as ex:
                        logger.debug('[get_user_report] Exception obtained. Reason:: {}'.format(ex))    
                    users_list.append(asset_info)
                print (users_list)
                logger.debug("The number of assets found {}".format(len(users_list)))
            else:
                raise Exception ("Not a valid Command")
        else:
            for each_id in extracted_ids:
                try:
                    asset_info          = {}
                    user_completed_jobs = list(db.jobs.aggregate([{"$match":{"user_id": each_id,"status":constants.JOB_STATUS_COMPLETED}},
                                                                    {"$group":{"_id":"$command","count": {"$sum":1}}
                                        }]))
                    user_failed_jobs    = list(db.jobs.aggregate([{"$match":{"user_id": each_id,"status":constants.JOB_STATUS_FAILED}},
                                                                    {"$group":{"_id":"$command","count": {"$sum":1}}
                                        }]))
                    completed_count_value = {data["_id"]: data["count"] for data in user_completed_jobs}
                    failed_count_value    = {data["_id"]: data["count"] for data in user_failed_jobs}
    
                    for command in commands:
                        temp = ""
                        if completed_count_value.get(command):
                            temp += str(completed_count_value[command]) + "(completed), "
                        else:
                            temp += str(0) + "(completed), "
                        
                        if failed_count_value.get(command):
                            temp += str(failed_count_value[command]) + "(failed)"
                        else:
                            temp += str(0) + "(failed)"
                    
                        asset_info[command] = temp                                          
                    username = db.users.find_one({"_id":ObjectId(each_id)},{"_id":0,"username":1})
                    asset_info["username"] = username.get("username")
                except Exception as ex:
                    logger.debug('[get_user_report] Exception obtained. Reason :: {}'.format(ex))    
                users_list.append(asset_info)
            print(users_list)
            logger.debug("The number of assets found {}".format(len(users_list)))
            
        if not info.get("download") :
            return {"user_data" : utils.json_friendly(users_list)}
        
        if users_list:
            xls_file = utils.write_content_to_xls_file(users_list, xls_heading_list, dict_keys, file_path)
            if not xls_file:
                bottle.abort(500, json.dumps({'errors':["Not able to create xls file"]}))        
            utils.delete_xls_reports(xls_file_path)
            return static_file(filename, xls_file_path, download=filename)
    except Exception as ex:
        logger.debug("[user_reports] Exception obtained :: {}".format(ex))

@app.route('/archived_files_report',method = 'GET')
def archived_files_report():
    """
    Generates reports for archived_files.
    Input  ex: {'/archived_files_report'} --> Generates xls report on all archived_files.
    Output returns xls static file.
    """
    info = json.loads(bottle.request.query.s) if bottle.request.query.s else {}
    logger.debug("[get_archived_files_report] Input info is: {}".format(info))

    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S")
    filename  = "archived_files_report" + timestamp + ".xlsx"

    if os.name == "posix":
        xls_file_path = "/opt/HSM3/Reports"
    else:
        xls_file_path = "C:\\Karthavya\\HSM3\\Reports"

    if not os.path.exists(xls_file_path):
        os.mkdir(xls_file_path)
        
    file_path        = os.path.join(xls_file_path, filename)
    xls_heading_list = ["Filename","Size","Archived Date","Pool1","Pool1 Archived Date",
                        "Pool2","Pool2 Archived Date","Pool3","Pool3 Archived Date",
                        "Pool4","Pool4 Archived Date",]
    dict_keys        = ["file_name","file_size","created_time","pool_id1","created_time1",
                        "pool_id2","created_time2","pool_id3","created_time3","pool_id4",
                        "created_time4"]
    archived_files   = []

    if info.get("from_date") and info.get("to_date"):
        archived_assets  = list(db.archive.find({"created_time":{"$gte":info["from_date"],"$lt": info["to_date"]}}).sort([("$natural",-1)]))
    else:
        archived_assets  = list(db.archive.find().sort([("$natural",-1)]))
    
    try:
        for asset in archived_assets:
            try:        
                asset_info                 = {}
                asset_info["file_name"]    = asset.get("file_name")
                filesize                   = asset.get("file_size")
                asset_info["file_size"]    = humanize.naturalsize(filesize)
                asset_info["created_time"] = asset.get("created_time")

                pool_no = 1
                for index, loc in enumerate(asset["archived_locations"]):
                    if loc.get("container_type") == constants.CONTAINER_TYPE_CACHE:
                        continue  
                    asset_info["pool_id{}".format(pool_no)]      = loc.get("pool_id","")
                    asset_info["created_time{}".format(pool_no)] = loc.get("created_time","")
                    pool_no += 1
                    
            except Exception as ex:
                logger.debug("[get_archived_file_report]Exception--> '{}'".format(ex))
                bottle.abort(500, json.dumps({"Errors":[str(ex)]}))  
            archived_files.append(asset_info)  
        print (archived_files)
        logger.info("[get_archived_files_report] Number of files found are '{}'".format(len(archived_files)))
        if not info.get("download") :
            return {"archived_assets" : utils.json_friendly(archived_files[:50])}
        if archived_files:
            xls_file = utils.write_content_to_xls_file(archived_files, xls_heading_list, dict_keys, file_path)
            if not xls_file:
                bottle.abort(500, json.dumps({"Errors": "Could not write content to xls file"}))
            utils.delete_xls_reports(xls_file_path)
            return static_file(filename, xls_file_path, download=filename)   
    except Exception as ex:
        logger.debug("[get_archived_file_report]Exception--> '{}'".format(ex))
        bottle.abort(500, json.dumps({"Errors":[str(ex)]}))  

@app.route('/inventory_report',method='GET')
def inventory_report():
    """
    Generates reports for inventory.
    Input  ex: {'/inventory_report'} --> Generates xls report on inventory.
           ex: {"container_id/barcode/label":"Disk3/11223344/News1"}
           ex: {"pool_name":"Dvd pool"}
           ex: {"pool_type":"DVD/LTO/DISK"}
           ex: {"rw":"True"}
           ex: {"from_date":"2019-07-29","to_date":"2019-09-30"}
           ex: {'combination of any of the above parameters'}
    Output returns xls static file.
    """
    try:
        info = json.loads(bottle.request.query.s) if bottle.request.query.s else {}
        logger.debug("[get_inventory_report] Input info is: {}".format(info))
    except Exception as ex:
        bottle.abort(404, json.dumps({"Errors":"Error in input info '{}'".format(ex)}))
    
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S")
    filename  = "inventory_report" + timestamp + ".xlsx"

    if os.name == "posix":
        xls_file_path = "/opt/HSM3/Reports"
    else:
        xls_file_path = "C:\\Karthavya\\HSM3\\Reports"

    if not os.path.exists(xls_file_path):
        os.mkdir(xls_file_path)
        
    file_path           = os.path.join(xls_file_path, filename)
    xls_heading_list    = ["Container ID","Container Label","Container Barcode","Container Type","Add to inventory Date",
                         "Total Space","Free Space","Total Files","Pool name","Pool type","Read Only"]
    dict_keys           = ["cont_id","cont_label","cont_barcode","cont_type","created_time","total_space",
                          "free_space","total_files","pool_name","pool_type","RW"]
    inventory_data_list = []
    inv_query           = {}            
    pool_query          = {}

    container_query     = []
    
    if info.get("container_info"):
        container_query.append({"container_id":{"$regex": ".*{}.*".format(info["container_info"]), "$options": "i"} } )
        container_query.append({"barcode":{"$regex": ".*{}.*".format(info["container_info"]), "$options": "i"} } )
        container_query.append({"label": {"$regex": ".*{}.*".format(info["container_info"]), "$options": "i"} } )
        inv_query["$or"] = container_query
    
    if info.get("pool_name"):
        pool_query["pool_name"] = info["pool_name"]

    if info.get("pool_type"):
        pool_query["type"] = info["pool_type"]
    
    if info.get("container_state",False) in [True, False]:
        inv_query["read_only"] = bool(info["container_state"])
    
    if info.get("from_date") and info.get("to_date"):
        inv_query["created_datetime"] = {"$gte":info["from_date"],"$lt": info["to_date"]}
    try:
        if pool_query:
            pool_data = list(db.pools.find(pool_query,{"_id":0, "pool_id":1,  "pool_name": 1}))
            pool_info = {pool["pool_id"]: pool["pool_name"] for pool in pool_data}
            inv_query["pool_id"] = {"$in": list(pool_info.keys())}

        inventory_data = list(db.inventory.find(inv_query).sort([("$natural",-1)]))
        
        if not pool_query:
            pool_ids  = [info_["pool_id"] for info_ in inventory_data]
            pool_info = {pool["pool_id"]: pool["pool_name"] for pool in db.pools.find({"pool_id": {"$in": pool_ids}})}
        
        mirror_containers = [mirror.get("mirror_containers") for mirror in inventory_data]
        mirr_list = []
        for mir_ in mirror_containers:
            if mir_ != None:
                val = [*mir_.values()]
                mirr_list.extend(val)      
        
        for cont in inventory_data:
            cont_info                    = {}
            cont_info["pool_name"]       = pool_info.get(cont["pool_id"])
            cont_info["pool_type"]       = cont.get("type")
            cont_info["cont_label"]      = cont.get("label")
            cont_info["total_files"]     = cont.get("number_of_archived_files")
            cont_info["RW"]              = cont.get("read_only")
            cont_info["cont_barcode"]    = cont.get("barcode")
            cont_info["created_time"]    = cont.get("created_datetime")
            cont_info["cont_id"]         = cont.get("container_id")
            total_size                   = utils.convert_size(cont["total_space"])
            free_space                   = utils.convert_size(cont["free_space"])
            cont_info["total_space"]     = (str(round(total_size[0],2))+ " " + total_size[1]) 
            cont_info["free_space"]      = (str(round(free_space[0],2))+ " " + free_space[1])         
        
            if len(mirr_list) != 0:
                for each in mirr_list:
                    if cont.get("container_id") == each:
                        cont_info["cont_type"] = "Mirror"
                    else:
                        cont_info["cont_type"] = "Primary"
            else:
                cont_info["cont_type"] = "Primary"
            
            inventory_data_list.append(cont_info)
        print (inventory_data_list)
    except Exception as ex:
        logger.debug("[get_inventory_report] Exception --> {}".format(ex))
        bottle.abort(500, json.dumps({"Errors":[str(ex)]}))
    logger.info("[get_inventory_report] Number of files found are '{}'".format(len(inventory_data_list)))
    if not info.get("download") :
        return {"inventory_data" : utils.json_friendly(inventory_data_list[:50])} 
    if inventory_data_list:
        xls_file = utils.write_content_to_xls_file(inventory_data_list, xls_heading_list, dict_keys, file_path)
        if not xls_file:
            bottle.abort(500, json.dumps({"Errors": "Could not write content to xls file"}))
        utils.delete_xls_reports(xls_file_path)
        return static_file(filename, xls_file_path, download=filename)

@app.route('/retrieved_files_report',method = 'GET')
def retrieved_files_report():
    """
    Generates reports for retrieved files.
    Input  ex: {'/retrieved_files_report'} --> Generates xls report on all retrieved files.
           ex: {"date":"2019-07-25"}       --> Generates xls report on retrieved files of that day.
    Output returns xls static file.
    """
    try:
        info = json.loads(bottle.request.query.s) if bottle.request.query.s else {}
        logger.debug("[get_retrieved_files_report] Input info is: {}".format(info))
    except Exception as ex:
        bottle.abort(404, json.dumps({"Errors":"Error in input info '{}'".format(ex)}))
    
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S")
    filename  = "retrieved_files_report" + timestamp + ".xlsx"

    if os.name == "posix":
        xls_file_path = "/opt/HSM3/Reports"
    else:
        xls_file_path = "C:\\Karthavya\\HSM3\\Reports"

    if not os.path.exists(xls_file_path):
        os.mkdir(xls_file_path)
        
    file_path             = os.path.join(xls_file_path, filename)
    xls_heading_list      = ["FileName","Size","Retrieved Date","Retrieved from","Retrieved to"]
    dict_keys             = ["file_name","file_size","retrieved_date","retrieve_from","retrieve_to"]
    retrieved_files_list  = []
    asset_info            = {}

    
    if info.get("from_date") and info.get("to_date"):
        retrieved_assets  = list(db.jobs.find({"command":constants.COMMAND_RETRIEVE,"created_datetime":{"$gte":info["from_date"],"$lt": info["to_date"]}}).sort([("$natural",-1)]))
    else:
        retrieved_assets  = list(db.jobs.find({"status": constants.JOB_STATUS_COMPLETED, "command":"Retrieve"}).sort([("$natural",-1)]))
    
    try:
        for asset in retrieved_assets:
            asset_info = {}
            try:
                asset_info["file_name"]      = asset.get("file_name","")
                filesize                     = asset.get("data",{}).get("file_size")
                asset_info["file_size"]      = humanize.naturalsize(filesize)
                asset_info["retrieved_date"] = asset.get("created_datetime","")
                asset_info["retrieve_from"]  = asset.get("data",{}).get("src_details",{}).get("bin_id",None)
                if asset_info["retrieve_from"] is None:
                    asset_info["retrieve_from"]  = asset.get("data",{}).get("src_details",{}).get("container_id",None)
                asset_info["retrieve_to"]    = asset.get("data",{}).get("dst_details",{}).get("bin_id")

            except Exception as ex:
                logger.debug("[get_retrieved_files_report] Exception --> '{}'".format(ex))
                bottle.abort(500, json.dumps({"Errors":[str(ex)]}))
            retrieved_files_list.append(asset_info)
        print (retrieved_files_list)
        logger.info("The number of assets found {}".format(len(retrieved_files_list)))
        if not info.get("download") :
            return {"retrieved_assets" : utils.json_friendly(retrieved_files_list[:50])}
        if retrieved_files_list:
            xls_file = utils.write_content_to_xls_file(retrieved_files_list, xls_heading_list, dict_keys, file_path)
            if not xls_file:
                bottle.abort(500, json.dumps({'errors':["Not able to create xls file"]}))
            utils.delete_xls_reports(xls_file_path)
            return static_file(filename, xls_file_path, download=filename)
    except Exception as ex:
        logger.debug("[get_retrieved_files_report] Exception -->'{}'".format(ex))
        bottle.abort(500, json.dumps({"Errors":[str(ex)]}))

@app.route('/audit_report',method='GET')
def audit_trial_report():
    """
    Generates report on audit logs.
    """
    try:
        info = json.loads(bottle.request.query.s) if bottle.request.query.s else {}
        logger.debug("[audit_trial_report] Input info is: {}".format(info))
    except Exception as ex:
        bottle.abort(404, json.dumps({"Errors":"Error in input info '{}'".format(ex)}))
    
    timestamp = time.strftime("%Y-%m-%d_%H:%M:%S")
    filename  = "audit_trial_report" + timestamp + ".xlsx"

    if os.name == "posix":
        xls_file_path = "/opt/HSM3/Reports"
    else:
        xls_file_path = "C:\\Karthavya\\HSM3\\Reports"

    if not os.path.exists(xls_file_path):
        os.mkdir(xls_file_path)
        
    file_path             = os.path.join(xls_file_path, filename)
    xls_heading_list      = ["UserName","LogTime","Action","Description"]
    dict_keys             = ["username","log_time","action","desc"]
    audit_logs_list       = []
    audit_info            = {}
    audit_query           = {}
    try:
        if info.get("username"):
            audit_query["username"] = info["username"]

        if info.get("action"):
            audit_query["action"] = info["action"]

        if info.get("from_date") and info.get("to_date"):
            audit_query["log_time"] = {"$gte":info["from_date"],"$lt": info["to_date"]}

        audit_data = list(db.user_log.find(audit_query).sort([("$natural",-1)]))

        for each in audit_data:
            each_info = {}
            each_info["username"] = each.get("username")
            each_info["log_time"] = each.get("log_time")
            each_info["action"]   = each.get("action")
            each_info["desc"]     = each.get("description")
            audit_logs_list.append(each_info)
        print(audit_logs_list)
    except Exception as ex:
        logger.debug("[audit_trial_report] Exception --> {}".format(ex))
        bottle.abort(500, json.dumps({"Errors":[str(ex)]}))
    logger.info("[audit_trial_report] Number of files found are '{}'".format(len(audit_logs_list)))
    if not info.get("download") :
        return {"audit_data" : utils.json_friendly(audit_logs_list[:50])} 
    if audit_logs_list:
        xls_file = utils.write_content_to_xls_file(audit_logs_list, xls_heading_list, dict_keys, file_path)
        if not xls_file:
            bottle.abort(500, json.dumps({"Errors": "Could not write content to xls file"}))
        return static_file(filename, xls_file_path, download=filename)

'''Tags'''
@app.route('/tags',method = 'GET')
@app.route('/tags/<tag_id>',method = 'GET')
def list_tags(tag_id = None):
    check_authorized()
    tag_details = None
    if tag_id:
        try:
            tag_details = db.tags.find_one({"_id":ObjectId(tag_id)})
            if not tag_details:
                raise Exception ("No data found")
        except Exception as ex:
            logger.debug('[list_one_tag] Exception Obtained --> {}'.format(ex))
            bottle.abort(404, json.dumps({'Errors':[str(ex)]}))
        return {"tag": utils.json_friendly(tag_details)}
    else:
        return {"tags":utils.json_friendly(list(db.tags.find()))}

@app.route('/tags/<tag_id>',method = 'DELETE')
def delete_tag(tag_id):
    check_authorized()
    try:
        remove_status = db.tags.remove({"_id":ObjectId(tag_id)})
        logger.info('[delete_tag] Tag successfully deleted with status {}'.format(remove_status))
    except Exception as ex:
        logger.debug('[delete_tag] Exception obtained --> {}'.format(ex))
        bottle.abort(404, json.dumps({'Errors':[str(ex)]}))

@app.route('/tags',method = 'POST')
def create_a_tag():
    user = check_authorized()
    new_tag = None
    add_tag = {}

    try:
        new_tag = json.loads(bottle.request.body.read()) 
    except Exception as ex:
        logger.debug('[create_a_tag] Exception obtained. Reason --> {}'.format(ex))
        bottle.abort(404, json.dumps({'Errors':[str(ex)]}))
    try:
        if new_tag:
            update_data = {}
            errors      = []
            valid_keys  = {"tag_name": str}
            utils.validate_keys(valid_keys, new_tag, update_data, errors)

            if errors:
                logger.error('[create_a_tag] Error is: {}'.format(errors))
                raise Exception("{}".format(errors))

            if new_tag.get("tag_name"):
                tag_name = new_tag["tag_name"].strip().lower().replace(" ","")
                if db.tags.find_one({"tag_name":tag_name}):
                    raise Exception ("Duplicate Tag name.")
                else:
                    add_tag["tag_name"] = tag_name
                    insert_status = db.tags.insert(add_tag)
                    logger.info('[create_a_tag] New tag created with id :"{}"'.format(insert_status))
                    log_status = db.user_log.insert({"username": user["username"],
                                    "log_time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": constants.CREATE,
                                    "description": "Tag '{}' created.".format(tag_name)})
                    logger.debug("[create_a_tag] user log insertion status: {}".format(log_status))
        else:
            raise Exception ('No new tag details obtained')
    except Exception as ex:
        logger.debug('[create_a_tag] Exception --> {}'.format(ex))
        bottle.abort(404, json.dumps({'Errors':[str(ex)]}))
    
@app.route('/tags/<tag_id>',method = 'PUT')
def update_a_tag(tag_id):
    check_authorized()
    old_tag     = {}
    new_tag     = None
    updated_tag = {}

    try:
        new_tag = json.loads(bottle.request.body.read()) 
    except Exception as ex:
        logger.debug('[update_a_tag] Exception obtained. Reason :: {}'.format(ex))
        bottle.abort(404, json.dumps({'Errors':[str(ex)]}))
    try:
        old_tag = db.tags.find_one({"_id": ObjectId(tag_id)})
        if not old_tag:
            raise Exception ("Not a valid TagID")
    
        if new_tag:
            update_data = {}
            errors      = []
            valid_keys  = {"tag_name": str}
            utils.validate_keys(valid_keys, new_tag, update_data, errors)

            if errors:
                logger.error('[update_a_tag] Error is: {}'.format(errors))
                raise Exception("{}".format(errors))

            if new_tag.get("tag_name"):
                tag_name = new_tag["tag_name"].strip().lower().replace(" ","")
                if old_tag["tag_name"] == tag_name or db.tags.find_one({"_id":{"$ne":ObjectId(tag_id)},"tag_name":tag_name}):
                    raise Exception ("Duplicate Tag name. No updation possible")
                else:
                    updated_tag["tag_name"] = tag_name
                    update_status = db.tags.update({"_id": ObjectId(tag_id)},{"$set":updated_tag}) 
                    logger.info('[update_a_tag] Updated successfully {}'.format(update_status))
                    log_status = db.user_log.insert({"username": user["username"],
                                    "log_time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": constants.UPDATE,
                                    "description": "Tag '{}' updated as '{}'.".format(old_tag["tag_name"],updated_tag["tag_name"])})
                    logger.debug("[update_a_tag] user log insertion status: {}".format(log_status))  
        else:
            raise Exception ('No new tag details obtained')
    except Exception as ex:
        logger.debug('[update_a_tag] Exception --> {}'.format(ex))
        bottle.abort(404, json.dumps({'Errors':[str(ex)]}))

'''Categories'''

@app.route('/categories',method = 'GET')    
@app.route('/categories/<category_id>',method = 'GET')
def list_categories(category_id = None):
    check_authorized()
    category_details = None
    if category_id:
        try:
            category_details = db.categories.find_one({"_id": ObjectId(category_id)})
            if not category_details:
                raise Exception ("No data found")
        except Exception as ex:
            logger.debug('[list_one_category] Exception --> {}'.format(ex))
            bottle.abort(404, json.dumps({'Errors':[str(ex)]}))
        return ({"category":utils.json_friendly(category_details)})
    else:
        return ({"categories":utils.json_friendly(list(db.categories.find()))}) 

@app.route('/categories/<category_id>',method = 'DELETE')
def delete_a_category(category_id):
    check_authorized()
    try:
        remove_status = db.categories.remove({"_id":ObjectId(category_id)})
        logger.info("[delete_a_category] Category Successfully deleted with status {}".format(remove_status))
    except Exception as ex:
        logger.debug('[delete_a_category] Exception --> {}'.format(ex))
        bottle.abort(404, json.dumps({'Errors':[str(ex)]}))

@app.route('/categories',method = 'POST')
def create_a_category():
    user = check_authorized()
    new_category = None
    add_category = {}

    try:
        new_category = json.loads(bottle.request.body.read())
    except Exception as ex:
        logger.debug('[create_a_category] Exception --> {}'.format(ex))
        bottle.abort(404,json.dumps({'Errors':[str(ex)]}))
    try:
        if new_category:
            update_data = {}
            errors      = []
            valid_keys  = {"category_name": str}
            utils.validate_keys(valid_keys, new_category, update_data, errors)
            
            if errors:
                logger.error('[create_a_category] Error is: {}'.format(errors))
                raise Exception("{}".format(errors))

            print("h1")
            if not isinstance(new_category["category_name"],str):
                raise Exception ("Category name not a string")
            if not new_category.get("category_name").strip():
                raise Exception ("Category name empty")
            if new_category.get("category_name"):
                category_name = new_category.get("category_name").strip().lower().replace(" ","")
                if db.categories.find_one({"category_name":category_name}):
                    raise Exception ("Category already exists")
                else:
                    add_category["category_name"] = category_name
                    insert_status = db.categories.insert(add_category)
                    logger.info('[create_a_category] New category created with id : {}'.format(insert_status))
                    log_status = db.user_log.insert({"username": user["username"],
                                                    "log_time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": constants.CREATE,
                                                    "description": "Category '{}' created.".format(category_name)})
                    logger.debug("[create_a_category] user log insertion status: {}".format(log_status))
        else:
            raise Exception ("No category details obtained")
    except Exception as ex:
        logger.debug('[create_a_category] Exception --> {}'.format(ex))
        bottle.abort(404,json.dumps({'Errors':[str(ex)]}))

@app.route('/categories/<category_id>',method = 'PUT')
def update_a_category(category_id):
    user = check_authorized()
    new_category     = None
    db_data          = {}
    updated_category = {}

    try:
        new_category = json.loads(bottle.request.body.read())
    except Exception as ex:
        logger.debug('[update_a_category] Exception obtained --> {}'.format(ex))
        bottle.abort(404,json.dumps({"Errors":[str(ex)]}))
    try:
        db_data = db.categories.find_one({"_id":ObjectId(category_id)})
        if not db_data:
            raise Exception("Category ID not valid")
        if new_category:
            update_data = {}
            errors      = []
            valid_keys  = {"category_name": str}
            utils.validate_keys(valid_keys, new_category, update_data, errors)
    
            if errors:
                logger.error('[update_a_category] Error is: {}'.format(errors))
                raise Exception("{}".format(errors))

            if new_category.get("category_name"):
                category_name = new_category.get("category_name").strip().lower().replace(" ","") 
                if db.categories.find_one({"_id":{"$ne":ObjectId(category_id)},"category_name":category_name}) or\
                    db_data["category_name"] == category_name:
                    raise Exception ("Duplicate Category Name. No updation possible")
                else:
                    updated_category["category_name"] = category_name
                    update_status = db.categories.update({"_id":ObjectId(category_id)},{"$set":updated_category})
                    logger.info('[update_a_category] Update status: {}'.format(update_status))
                    log_status = db.user_log.insert({"username": user["username"],
                                                    "log_time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": constants.UPDATE,
                                                    "description": "Category '{}' updated as '{}'.".format(db_data["category_name"],updated_category["category_name"])})
                    logger.debug("[update_a_category] user log insertion status: {}".format(log_status))
        else:
            raise Exception ("No category details obtained")
    except Exception as ex:
        logger.debug('[update_a_category] Exception--> {}'.format(ex))
        bottle.abort(404,json.dumps({"Errors":[str(ex)]}))
