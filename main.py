from flask import Flask, make_response, request, render_template
from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
import uuid, datetime, urllib.parse


app = Flask(__name__)
api = Api(app)
app.url_map.strict_slashes = False
app.config['JSON_SORT_KEYS'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounts.db'
app.config['SQLALCHEMY_BINDS'] = {'transactions': 'sqlite:///transactions.db'}
db = SQLAlchemy(app)

class AccountsModel(db.Model):
    accountId = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    surname = db.Column(db.String(20), nullable=False)
    total = db.Column(db.Float, nullable=False)

class TransactionsModel(db.Model):
    __bind_key__ = 'transactions'
    uuid = db.Column(db.String(36), primary_key=True)
    senderId = db.Column(db.String(20), nullable=False, default='')
    receiverId = db.Column(db.String(20), nullable=False, default='')
    date = db.Column(db.String(26), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    divert = db.Column(db.Boolean, nullable=False, default=None)
    amount = db.Column(db.Float, nullable=False)

account_post_args = reqparse.RequestParser()
account_post_args.add_argument("name", type=str)
account_post_args.add_argument("surname", type=str)

accountid_post_args = reqparse.RequestParser()
accountid_post_args.add_argument("amount", type=float)

accountid_put_args = reqparse.RequestParser()
accountid_put_args.add_argument("name", type=str)
accountid_put_args.add_argument("surname", type=str)

accountid_patch_args = reqparse.RequestParser()
accountid_patch_args.add_argument("name", type=str)
accountid_patch_args.add_argument("surname", type=str)

transfer_post_args = reqparse.RequestParser()
transfer_post_args.add_argument("from", type=str)
transfer_post_args.add_argument("to", type=str)
transfer_post_args.add_argument("amount", type=float)

divert_post_args = reqparse.RequestParser()
divert_post_args.add_argument("id", type=str)

def get_base_url(url, with_path=False):
    parsed = urllib.parse.urlparse(url)
    path   = '/'.join(parsed.path.split('/')[:-1]) if with_path else ''
    parsed = parsed._replace(path=path)
    parsed = parsed._replace(params='')
    parsed = parsed._replace(query='')
    parsed = parsed._replace(fragment='')
    return parsed.geturl()

def abort_if_false_id(accountId):
    account = AccountsModel.query.filter_by(accountId=accountId).all()
    if account == []:
        abort(404, message="Account id not found")

def create_new_transaction(amount, type, accountId, receiverId=None, divert=None):
    abort_if_false_id(accountId)
    if divert == None:
        divert = True
    if type == "Withdraw":
        senderId = accountId
        receiverId = ""
    elif type == "Deposit":
        receiverId = accountId
        senderId = ""
    elif type == "Send" or type == "Receive" or type == "Divert Send" or type == "Divert Receive" or type == "Useless":
        senderId = accountId
    else:
        abort(400, message="Error transaction type")
    trans_id = str(uuid.uuid4())
    date = str(datetime.datetime.now())
    trans = TransactionsModel(uuid=trans_id, senderId=senderId, receiverId=receiverId, date=date, type=type, divert=divert, amount=amount)
    db.session.add(trans)
    db.session.commit()
    result = {
        "uuid": trans_id,
        "senderId": senderId,
        "receiverId": receiverId,
        "date": date,
        "type": type,
        "divert": divert,
        "amount": amount
    }
    return result

resource_transactions = {
    "uuid": fields.String,
    "senderId": fields.String,
    "receiverId": fields.String,
    "date": fields.String,
    "type": fields.String,
    "amount": fields.Float(2)
}
@marshal_with(resource_transactions)
def serialize_transaction(trans):
    return trans

resource_fields_accounts = {
    "accountId" : fields.String,
    "name": fields.String,
    "surname": fields.String,
    "total": fields.Float(2)
}

@marshal_with(resource_fields_accounts)
def serialize_account(account):
    return account

# /api/account
class Account(Resource):
    @marshal_with(resource_fields_accounts)
    def get(self):
        accounts = AccountsModel.query.all()
        result_dict = [t.__dict__ for t in accounts]
        return result_dict

    def post(self): # request body: name, surname
        id = str(uuid.uuid4().hex[:20])
        args = account_post_args.parse_args()
        if args["name"] == None and args["surname"] == None:
            abort(400, message="Name and surname are required")
        elif args["name"] == None or args["name"] == "":
            abort(400, message="Name is required")
        elif args["surname"] == None or args["surname"] == "":
            abort(400, message="Surname is required")
        account = AccountsModel(accountId=id, name=args["name"], surname=args["surname"], total=0)
        db.session.add(account)
        db.session.commit()
        id_dict = {
            "accountId": id 
        }
        return id_dict, 201

    def delete(self): 
        accountId = request.args.get('id', type=str)
        if accountId == None or accountId == '':
            abort(400, message="AccountId is required")
        abort_if_false_id(accountId)
        AccountsModel.query.filter_by(accountId=accountId).delete()
        db.session.commit()
        return 204

# /api/account/accountId
class AccountId(Resource):
    def get(self, accountId): 
        abort_if_false_id(accountId)
        account = AccountsModel.query.filter_by(accountId=accountId).first()
        name = account.name
        surname = account.surname
        total = account.total
        send_trans = TransactionsModel.query.filter_by(senderId=accountId, type="Send")
        useless_trans = TransactionsModel.query.filter_by(senderId=accountId, type="Useless")
        withdraw_trans = TransactionsModel.query.filter_by(senderId=accountId, type="Withdraw")
        divert_send_trans = TransactionsModel.query.filter_by(senderId=accountId, type="Divert Send")
        divert_receive_trans = TransactionsModel.query.filter_by(receiverId=accountId, type="Divert Receive")
        receive_trans = TransactionsModel.query.filter_by(receiverId=accountId, type="Receive")
        deposit_trans = TransactionsModel.query.filter_by(receiverId=accountId, type="Deposit")
        all_trans = (
            send_trans.union(useless_trans, withdraw_trans, divert_send_trans, divert_receive_trans, receive_trans, deposit_trans)
            .order_by(TransactionsModel.date.asc())
            .all()
        )
        data = {
            "name": name,
            "surname": surname,
            "total": total,
            "transactions": serialize_transaction(all_trans)
        }
        header_str = name + ";" + surname
        resp = make_response(data, 200)
        resp.headers['X-Sistema-Bancario'] = header_str
        return resp

    def post(self, accountId): # request body: amount
        abort_if_false_id(accountId)
        args = accountid_post_args.parse_args()
        try:
            amount = float(args["amount"])
            if amount == 0.0:
                amount = 0.0
        except  ValueError:
            abort(400, message="The amount must be a number")
        if args["amount"] == None:
            abort(400, message="Transaction amount is required")
        old_total = AccountsModel.query.filter_by(accountId=accountId).first().total
        if amount < 0 and (float(old_total) + amount) < 0:
            abort(400, message="Not enough money on the account")
        new_total = format(float(old_total) + amount, '.2f')
        if amount == 0:
            trans = create_new_transaction(amount, "Useless", accountId)
        elif amount < 0:
            trans = create_new_transaction(amount, "Withdraw", accountId)
        elif amount > 0:
            trans = create_new_transaction(amount, "Deposit", accountId)
        else:
            abort(400, message="Transaction amount error")
        AccountsModel.query.filter_by(accountId=accountId).first().total = new_total
        db.session.commit()
        res = {
            "transaction": trans,
            "total": new_total
            }
        resp = make_response(res, 200)
        return resp

    def put(self, accountId): # request body: name, surname
        abort_if_false_id(accountId)
        args = accountid_put_args.parse_args()
        if args["name"] == None and args["surname"] == None:
            abort(400, message="Name and surname are required")
        elif args["name"] == None:
            abort(400, message="Name is required")
        elif args["surname"] == None:
            abort(400, message="Surname is required")
        account = AccountsModel.query.filter_by(accountId=accountId).first()
        account.name = args["name"]
        account.surname = args["surname"]
        db.session.commit()
        return 200

    def patch(self, accountId): # request body: name or surname
        abort_if_false_id(accountId)
        args = accountid_patch_args.parse_args()
        account = AccountsModel.query.filter_by(accountId=accountId).first()
        if args["name"] == None and args["surname"] == None:
            abort(400, message="Name or surname required")
        elif args["name"] != None and args["surname"] != None:
            abort(400, message="Only name or surname is required. Use PUT method to change both.")
        elif args["name"] != None:
            account.name = args["name"]
        elif args["surname"] != None:
            account.surname = args["surname"]
        db.session.commit()
        return 200

    def head(self, accountId):
        abort_if_false_id(accountId)
        account = AccountsModel.query.filter_by(accountId=accountId).first()
        name = account.name
        surname = account.surname
        resp = make_response()
        resp.headers['X-Sistema-Bancario'] = name + ";" + surname
        return resp

# /api/transfer
class Transfer(Resource):
    def post(self): # request body: from, to, amount 
        args = transfer_post_args.parse_args()
        senderId = args["from"]
        receiverId = args["to"]
        amount = args["amount"]
        if senderId == None or senderId == "":
            abort(400, message="senderId is required")
        elif receiverId == None or receiverId == "":
            abort(400, message="receiverId is required")
        elif amount == None:
            abort(400, message="Transaction amount is required")
        abort_if_false_id(senderId)
        abort_if_false_id(receiverId)

        amount = float(args["amount"])        
        sender_account = AccountsModel.query.filter_by(accountId=senderId).first()
        receiver_account = AccountsModel.query.filter_by(accountId=receiverId).first()
        old_sender_total = float(sender_account.total)
        old_receiver_total = float(receiver_account.total)
        
        if amount < 0:
            abort(400, message="Error negative amount")
        if (old_sender_total - amount) < 0:
            abort(400, message="Not enough money on sender's account")
        else:
            if sender_account == receiver_account:
                new_sender_total = format(old_sender_total, '.2f')
                new_receiver_total = format(old_receiver_total, '.2f')
            else:
                new_sender_total = format(old_sender_total - amount, '.2f')
                new_receiver_total = format(old_receiver_total + amount, '.2f')

            sender_account.total = new_sender_total
            receiver_account.total = new_receiver_total
            send_trans = create_new_transaction(amount*(-1), "Send", senderId, receiverId, False)  
            receive_trans = create_new_transaction(amount, "Receive", senderId, receiverId, True)
            send_type = send_trans["type"]
            receive_type = receive_trans["type"]
            send_date = send_trans["date"]
            receive_date = receive_trans["date"]
            resp = make_response({
                    "send_uuid": send_trans['uuid'],
                    "sender_total": new_sender_total,
                    "send_type": send_type,
                    "send_date": send_date,
                    "receive_uuid": receive_trans['uuid'],
                    "receive_type": receive_type,
                    "receive_date": receive_date,
                    "receiver_total": new_receiver_total,
                    "amount": amount
                }, 200)
            return resp

# /api/divert
class Divert(Resource): # request body: transaction id
    def post(self):
        args = divert_post_args.parse_args()
        if args["id"] == None or args["id"] == "":
            abort(400, message="Transaction id is required")
        elif TransactionsModel.query.filter_by(uuid=args["id"]).all() == []:
            abort(404, message="Transaction id not found")
        
        trans = TransactionsModel.query.filter_by(uuid=args["id"]).first()
        if trans.type == "Send" and trans.divert == True:
            abort(400, message="Error. Already diverted.")
        elif trans.type != "Send" or trans.divert == True:
            abort(400, message="Error. Transaction id is not valid.")
        amount = trans.amount*(-1)
        senderId = trans.senderId
        sender_account = AccountsModel.query.filter_by(accountId=senderId).first()
        receiverId = trans.receiverId
        receiver_account = AccountsModel.query.filter_by(accountId=receiverId).first()
        abort_if_false_id(senderId)
        abort_if_false_id(receiverId)
        old_sender_total = float(sender_account.total)
        old_receiver_total = float(receiver_account.total)
        if (old_receiver_total - amount) < 0:
            abort(400, message="Error. Not enough money on the receiver's account")
        else:
            if sender_account == receiver_account:
                sender_account.total = format(old_sender_total, '.2f')
            else:
                sender_account.total = format(old_sender_total + amount, '.2f')
                receiver_account.total = format(old_receiver_total - amount, '.2f')
            trans.divert = True
            receiver_divert = create_new_transaction(amount*(-1), "Divert Send", receiverId, senderId, True)
            sender_divert = create_new_transaction(amount, "Divert Receive", receiverId, senderId, True)
            resp = make_response({
                "divert_transactions":[
                    receiver_divert,
                    sender_divert
                ]
            }, 200)
            return resp

@app.route("/", methods=["GET"], endpoint="search")
def search():
    return render_template('search.html')

@app.route("/transfer", methods=["GET"], endpoint="transfer")
def transfer():
    return render_template('transfer.html')

@app.route("/account", methods=["GET"], endpoint="account")
def account():
    return render_template("account.html")

@app.route("/accounts", methods=["GET"], endpoint="accounts")
def accounts():
    return render_template("accounts.html")

@app.route("/divert", methods=["GET"], endpoint="divert")
def divert():
    return render_template("divert.html")

@app.route("/cash", methods=["GET"], endpoint="cash")
def cash():
    return render_template("cash.html")

@app.route("/delete", methods=["GET"], endpoint="delete")
def delete():
    return render_template("delete.html")

api.add_resource(Account, "/api/account", endpoint="account_api")
api.add_resource(AccountId, "/api/account/<string:accountId>", endpoint="accountid_api")
api.add_resource(Transfer, "/api/transfer", endpoint="transfer_api")
api.add_resource(Divert, "/api/divert", endpoint="divert_api")

if __name__ == "__main__":
    app.run(debug=True)
