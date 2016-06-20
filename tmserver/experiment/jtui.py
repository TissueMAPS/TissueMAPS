from flask.ext.jwt import jwt_required


@jtui.route('/get_available_jtmodules', methods=['GET'])
@jwt_required()
def get_available_jtmodules():
    print 'YEAH'

