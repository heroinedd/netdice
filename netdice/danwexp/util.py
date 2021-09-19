import os
import json

if __name__ == '__main__':
    input_dir = 'e:/study/MyTool/netdice/netdice/danwexp/input/mrinfo'
    for net in os.listdir(input_dir):
        property_file = os.path.join(input_dir, net, 'property.json')
        config_file = os.path.join(input_dir, net, 'config.json')
        scenarios = []
        with open(property_file) as pf:
            tmp = json.load(pf)
            for one in tmp['scenarios']:
                scenario = {
                    'rrs': one['rrs'],
                    'brs': one['brs'],
                    'point': int(one['property'].split(',')[-1].split(')')[0].strip()),
                    'probability': one['finished']['p_property']
                }
                scenarios.append(scenario)
        scenarios.sort(key=lambda x: x['probability'])
        with open(config_file, 'w', encoding='utf-8') as cf:
            json.dump({
                'rrs': scenarios[-1]['rrs'],
                'brs': scenarios[-1]['brs'],
                'point': scenarios[-1]['point']
            }, cf, indent=4)
