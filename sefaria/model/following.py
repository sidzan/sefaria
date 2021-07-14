"""
following.py - handle following relationships between users

Writes to MongoDB Collection: following
"""
from datetime import datetime

from sefaria.system.database import db


class FollowRelationship(object):
	def __init__(self, follower=None, followee=None):
		self.follower = follower
		self.followee = followee
		self.follow_date = datetime.now()

	def exists(self):
		bool(db.following.find_one({"follower": self.follower, "followee": self.followee}))

	def follow(self):
		from sefaria.model.notification import Notification

		db.following.save(vars(self))

		# Notification for the Followee
		notification = Notification({"uid": self.followee})
		notification.make_follow(follower_id=self.follower)
		notification.save()
		
		return self

	def unfollow(self):
		db.following.remove({"follower": self.follower, "followee": self.followee})


class FollowSet(object):
	def __init__(self):
		self.uids = []
		return self

	@property
	def count(self):
		return len(self.uids)


class FollowersSet(FollowSet):
	def __init__(self, uid):
		self.uids = db.following.find({"followee": uid}).distinct("follower")


class FolloweesSet(FollowSet):
	def __init__(self, uid):
		self.uids = db.following.find({"follower": uid}).distinct("followee")


creators = None
def general_follow_recommendations(lang="english", n=4):
	"""
	Recommend people to follow without any information about the person we're recommending for.
	"""
	from random import choices
	from django.contrib.auth.models import User
	from sefaria.system.database import db

	global creators
	if not creators:
		creators = []
		match_stage = {"status": "public"} if lang == "english" else {"status": "public", "sheetLanguage": "hebrew"}
		pipeline = [
			{"$match": match_stage},
			{"$sortByCount": "$owner"},
			{"$lookup": {
				"from": "profiles",
				"localField": "_id",
				"foreignField": "id",
				"as": "user"}},
			{"$unwind": {
				"path": "$user",
				"preserveNullAndEmptyArrays": True
			}}
		]
		results = db.sheets.aggregate(pipeline)
		try:
			profiles = {r["user"]["id"]: r for r in results}
		except KeyError:
			logger.error("Encountered sheet owner with no profile record.  No users will be recommended for following.")
			profiles = {}
		user_records = User.objects.in_bulk(profiles.keys())
		creators = []
		for id, u in user_records.items():
			fullname = u.first_name + " " + u.last_name
			user = {
				"name": fullname,
				"url": "/profile/" + profiles[id]["user"]["slug"],
				"uid": id,
				"image": profiles[id]["user"]["profile_pic_url_small"],
				"organization": profiles[id]["user"]["organization"],
				"sheetCount": profiles[id]["count"],  
			}
			creators.append(user)
		creators = sorted(creators, key=lambda x: -x["sheetCount"])

	top_creators = creators[:1300]
	recommendations = choices(top_creators, k=n)

	return recommendations