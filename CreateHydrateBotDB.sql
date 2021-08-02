CREATE TABLE guildsettings
(
    guildid text,
    timoutduration integer,
    remindertime integer,
    vctextchannelid text,
    PRIMARY KEY (guildid)
);

CREATE TABLE vcchannels
(
    vctextchannelid text,
	guildid text,
    PRIMARY KEY (vctextchannelid)
);

CREATE TABLE guildsettings
(
    member text,
    lasthydrationreminder timestamp without time zone,
    vcchannelid text,
    vcleavetime timestamp without time zone,
    PRIMARY KEY (member)
);