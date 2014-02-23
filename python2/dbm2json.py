if __name__ == '__main__':
    import sys
    if sys.argv[1:]:
        filename = sys.argv[1]

        import json
        import dbm
        from os.path import splitext

        dbm_dict = dbm.open(filename, 'r')
        temp_dict = dict()
        temp_dict.update(dbm_dict)
        dbm_dict.close()

        with open('%s.json' % splitext(filename)[0], 'w') as json_file:
            json.dump(temp_dict, json_file)



