if __name__ == '__main__':
    import sys
    if sys.argv[1:]:
        filename = sys.argv[1]

        import json
        import dbm
        from os.path import splitext

        with open(filename, 'r') as json_file:
            temp_dict = json.load(json_file)

        dbm_dict = dbm.open('%s.dbm' % splitext(filename)[0], 'n')

        for key, value in temp_dict.iteritems():
            dbm_dict[key] = value

        dbm_dict.close()
