

from bge import logic

from game3 import keymap, player, HUD


class InventoryRed(HUD.Inventory):

	def ST_Startup(self):
		self.objects["Items"].localPosition = (-10, -17, 0)
		self.objects["Items"].localOrientation = self.createMatrix(deg=True, rot=[0,0,90])

class LayoutRed(player.ActorLayout):

	MODULES = [HUD.Stats, HUD.Aircraft, InventoryRed, HUD.Weapons]


class RedPlayer(player.CorePlayer):

	NAME = "Red"
	MESH = "Red"
	CLASS = "Standard"
	WP_TYPE = "MELEE"
	HAND = {"MAIN":"Hand_L", "OFF":"Hand_R"}
	INVENTORY = {"Back":"INV_JetPack"}
	OFFSET = (0, 0.1, 0.1)
	SPEED = 0.1
	JUMP = 5
	EYE_H = 1.658
	EDGE_H = 2.0

	def ST_Startup(self):
		self.data["CAMERA"]["Zoom_Old"] = self.data["CAMERA"].get("Zoom_Old", self.data["CAMERA"]["Zoom"])

		if self.data.get("ACTIVE_STATE", None) == "ST_Flying" and self.objects["Root"] != None:
			self.ST_Advanced_Set("Load")

	def ST_Advanced_Set(self, load=None):

		keymap.MOUSELOOK.center()

		self.setPhysicsType("RIGID")
		self.objects["Root"].setDamping(0.8, 0.9)

		if load == None:
			vref = self.objects["VertRef"].getAxisVect((0,1,0))
			self.objects["Root"].alignAxisToVect((0,0,-1), 1, 1.0)
			self.objects["Root"].alignAxisToVect(vref, 2, 1.0)
			if self.jump_state == "NONE":
				self.objects["Root"].worldLinearVelocity[2] = 6
			self.data["CAMERA"]["Zoom_Old"] = self.data["CAMERA"]["Zoom"]

		self.objects["CamRot"].localPosition = (0,0,0)
		self.objects["CamRot"].localOrientation = self.createMatrix(rot=(90,0,0))
		self.objects["VertRef"].worldOrientation = self.objects["Root"].worldOrientation.copy()

		logic.HUDCLASS.setControl(self, layout=LayoutRed)

		self.jump_state = "FLYING"
		self.data["CAMERA"]["Orbit"] = False
		self.data["HUD"]["Target"] = None
		self.data["HUD"]["Power"] = 0
		self.data["HUD"]["Lift"] = 0
		self.data["HUD"]["Forward"] = [0,0,1]

		self.active_state = self.ST_Flying

	def ST_Walking_Set(self):
		keymap.MOUSELOOK.center()

		self.jump_state = "FALLING"
		self.data["CAMERA"]["Zoom"] = self.data["CAMERA"]["Zoom_Old"]
		self.data["CAMERA"]["Orbit"] = True

		self.alignCamera(axis=(0,0,1))
		self.objects["VertRef"].localPosition = (0,0,0)
		self.objects["CamRot"].localOrientation = self.createMatrix()

		self.setPhysicsType("DYNAMIC")
		self.objects["Root"].setDamping(0, 0)

		logic.HUDCLASS.setControl(self)

		self.doAnim(STOP=True)
		self.setCameraEye()
		self.alignPlayer()

		self.active_state = self.ST_Walking

	def ST_Flying(self):
		owner = self.objects["Root"]
		linWV = owner.worldLinearVelocity

		wall = self.checkWall(axis=owner.getAxisVect((0,0,1)), simple=1)

		if keymap.BINDS["TOGGLEMODE"].tap() == True:
			self.ST_Walking_Set()
			return
		if wall != None:
			if "COLLIDE" not in wall[0]:
				self.ST_Walking_Set()
				return

		owner.applyForce((0, 0, -owner.scene.gravity[2]), False)

		move = self.motion["Move"]
		rotate = self.motion["Rotate"]

		ORIX = owner.localOrientation[2][0]
		ORIY = owner.localOrientation[2][2]

		POWER = (25-(ORIY*20))
		POWER = POWER+(POWER*(move[1]*0.5))
		DRAG = move[1]*-0.2

		BANK = ((rotate[2]*0.5)-(rotate[2]*DRAG))
		PITCH = ((rotate[0]*1)-(rotate[0]*DRAG))
		YAW = ((move[0]*0.4)-(move[0]*DRAG))

		YAWROLL = (ORIX*-0.4)+(YAW*(abs(0.8*ORIX)+0.2))

		owner.applyForce((0, 0, POWER), True)
		owner.applyTorque((-PITCH, YAWROLL, -BANK), True)

		self.doAnim(NAME="Flying", FRAME=(0,0), MODE="LOOP", BLEND=15)

		self.data["HUD"]["Power"] = (1+move[1])*50

		## Slow Camera ##
		self.data["CAMERA"]["Zoom"] = 5

		rpos = owner.worldPosition.copy()
		rquat = owner.worldOrientation.to_quaternion()
		vquat = self.objects["VertRef"].worldOrientation.to_quaternion()

		slowQ = vquat.slerp(rquat, 0.1)

		self.objects["VertRef"].worldPosition = rpos-(linWV*0.05)
		self.objects["VertRef"].worldOrientation = slowQ.to_matrix()


class BluePlayer(player.CorePlayer):

	NAME = "Blue"
	MESH = "Blue"
	CLASS = "Standard"
	WP_TYPE = "MELEE"
	INVENTORY = {"Shoulder_R": "WP_DemoStaff"}
	OFFSET = (0, 0.05, 0.2)
	SPEED = 0.12
	JUMP = 6
	EYE_H = 1.527
	EDGE_H = 1.85
	ACCEL = 15

	def defaultData(self):
		dict = {"WALLJUMPS":0}
		return dict

	def findWall(self):
		wall, nrm = self.checkWall()

		if wall > 100 and nrm != None:
			return True
		return False

	def wallJump(self, nrm):
		owner = self.objects["Root"]
		axis = nrm.copy()
		axis[2] = 0
		axis.normalize()

		self.alignPlayer(axis=axis)

		self.data["ENERGY"] -= 10

		nrm[2] += 1.5
		nrm.normalize()
		owner.worldLinearVelocity = nrm*self.data["JUMP"]

		#self.doPlayerAnim("JUMP")
		self.doAnim(NAME="WallJump", FRAME=(0,2), PRIORITY=2, MODE="PLAY", BLEND=2)

	def ST_Walking_Set(self):
		self.doAnim(STOP=True)
		self.data["WALLJUMPS"] = 0
		self.active_state = self.ST_Walking

	def ST_Advanced_Set(self, wall=None):
		owner = self.objects["Root"]

		if wall == None:
			wall = self.findWall()

		if wall == True and owner.localLinearVelocity[2] > -4 and self.data["ENERGY"] > 15:
			owner.setDamping(0, 0)
			self.data["HUD"]["Target"] = None
			self.data["WALLJUMPS"] = 0
			self.rayorder = "NONE"
			self.active_state = self.ST_Wall

	def ST_Wall(self):
		owner = self.objects["Root"]

		ground, angle, slope = self.checkGround()

		wall, nrm = self.checkWall()
		self.checkEdge()

		if self.jump_state == "EDGE":
			self.ST_Hanging_Set()
			return

		if ground != None and self.data["WALLJUMPS"] != 0:
			if owner.localLinearVelocity[2] < 0.1:
				self.ST_Walking_Set()
				return

		self.jump_state = "FALLING"
		self.rayorder = "NONE"

		if nrm != None and wall > 100:
			self.doAnim(NAME="WallJump", FRAME=(0,0), PRIORITY=3, MODE="LOOP", BLEND=10)
			if self.data["WALLJUMPS"] == 0 or keymap.BINDS["PLR_JUMP"].tap() == True or keymap.BINDS["TOGGLEMODE"].tap() == True:
				if self.data["ENERGY"] > 15:
					self.wallJump(nrm)
					self.data["WALLJUMPS"] += 1
		else:
			self.doPlayerAnim("FALLING")

		if self.motion["Move"].length > 0.01:
			move = self.motion["Move"].normalized()
			vref = self.objects["VertRef"].getAxisVect((move[0], move[1], 0))
			owner.applyForce((vref[0]*5, vref[1]*5, 0), False)

		self.objects["Character"]["DEBUG1"] = self.rayorder
		self.objects["Character"]["DEBUG2"] = str(self.jump_state)

		if owner.localLinearVelocity[2] < -2 :
			self.ST_Walking_Set()

	def ST_Hanging(self):
		owner = self.objects["Root"]

		super().ST_Hanging()

		if keymap.BINDS["TOGGLEMODE"].tap() == True:
			wall = self.findWall()
			if wall == True:
				self.ST_EdgeFall_Set()
				self.ST_Advanced_Set(wall)
				self.rayorder = "END"


class PurplePlayer(player.CorePlayer):

	NAME = "Purple"
	MESH = "Purple"
	CLASS = "Standard"
	WP_TYPE = "MELEE"
	OFFSET = (0, 0.05, 0.2)
	SPEED = 0.09
	JUMP = 4
	EYE_H = 1.515
	EDGE_H = 1.85

	def ST_Startup(self):
		self.wave_vis = True
		self.wave_from = None
		self.wave_to = None
		self.wave_dist = 0
		self.wave_timer = None
		self.active_post.append(self.getWaveTeleport)

	def ST_Advanced_Set(self):
		scene = player.base.SC_SCN

		mesh = self.objects["Mesh"]
		name = self.objects["Character"].name

		mesh_aoe = scene.objectsInactive[name+".Mesh.aoe"].meshes[0]
		mesh_vis = scene.objectsInactive[name+".Mesh"].meshes[0]

		if self.wave_vis == True:
			mesh.replaceMesh(mesh_aoe)
			self.wave_vis = False
		else:
			mesh.replaceMesh(mesh_vis)
			self.wave_vis = True

	def ST_Teleport_Set(self):
		owner = self.objects["Root"]

		if self.wave_to != None:
			self.objects["Character"].setVisible(False, True)
			#self.objects["Root"].setLinearVelocity((0,0,0), True)
			self.data["HUD"]["Target"] = None

			if keymap.BINDS["PLR_DUCK"].active() == True:
				self.wave_to[2] += 0.6
			else:
				self.wave_to[2] += 1

			V = owner.getVectTo(self.wave_to)
			self.alignPlayer(axis=V[1])
			self.doAnim(STOP=True)

			#self.jump_state = "FALLING"
			self.wave_timer = self.wave_dist
			self.wave_from = owner.worldPosition.copy()

			self.active_state = self.ST_Teleport
			self.setPhysicsType("NONE")

	def ST_Teleport(self):
		owner = self.objects["Root"]

		owner.worldLinearVelocity = (0,0,0)

		if self.wave_timer != None:
			fac = self.wave_timer/self.wave_dist
			point = self.wave_to.lerp(self.wave_from, fac)

			self.wave_timer -= 2
			self.data["ENERGY"] -= 2

			if fac < 0:
				self.wave_from = None
				self.wave_timer = None
				point = self.wave_to

			owner.worldPosition = point

		else:
			self.ST_Walking_Set()
			self.doCrouch( keymap.BINDS["PLR_DUCK"].active() )

	def ST_Walking_Set(self):
		self.objects["Character"].setVisible(True, True)
		self.active_state = self.ST_Walking
		self.setPhysicsType("DYNAMIC")
		self.objects["Root"].worldLinearVelocity = (0,0,0)

	def getWaveTeleport(self):
		owner = self.objects["Root"]

		if keymap.BINDS["ALTACT"].tap() == True and self.wave_from == None:
			self.ST_Teleport_Set()

		if self.rayhit != None and self.wave_from == None:
			self.wave_to = None
			self.wave_dist = self.rayvec.length
			if self.wave_dist < self.data["ENERGY"] and self.wave_dist > 3:
				angle = self.createVector(vec=[0,0,1]).angle(self.rayhit[2], 0)
				angle = round(self.toDeg(angle), 2)
				if angle <= self.SLOPE:
					rayto = self.rayhit[1].copy()
					rayto[2] += 1
					rayfrom = self.rayhit[1].copy()
					rayfrom[2] += 0.1
					if owner.rayCast(rayto, rayfrom, 1.8, "GROUND", 1, 1, 0)[0] == None:
						self.data["HUD"]["Color"] = (1, 0, 1, 1)
						self.wave_to = self.rayhit[1].copy()

