class Channel:

    def __init__(self):
        self.id = 0
        self.volume = 0
        self.source = 0
        self.powerOn = False
        self.mute = False
        self.treble = 7
        self.bass = 7
        self.balance = 31

    def __str__(self):
        return "Id: {}\nPwr: {}\nMute:{}\nSource: {}\nVol: {}\n Treble: {}, Bass: {}, Bal: {}"\
            .format(self.id, self.powerOn, self.mute, self.source, self.volume, self.treble, self.bass, self.balance)

    def toDict(self):
        vals = {}
        vals["id"] = self.id
        vals["volume"] = self.volume
        vals["source"] = self.source
        vals["powerOn"] = self.powerOn
        vals["mute"] = self.mute
        vals["treble"] = self.treble
        vals["bass"] = self.bass
        vals["balance"] = self.balance
        return vals