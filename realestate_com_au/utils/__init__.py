def delete_nulls(obj):
    new_obj = {}
    for key, val in obj.items():
        if val is not None:
            if isinstance(val, dict):
                new_obj[key] = delete_nulls(val)
            else:
                new_obj[key] = val
    return new_obj
