

CREATE TABLE account (
    owner PRIMARY KEY NOT NULL,
    number UNIQUE NOT NULL,
    password NOT NULL
);

CREATE TABLE roster (
    owner NOT NULL,
    number NOT NULL,
    FOREIGN KEY(owner) REFERENCES account(owner)
);

CREATE TABLE files (
    path NOT NULL,
    reciever,
    frm,
    read,
    password
);

CREATE TABLE avatars (
    owner PRIMARY KEY NOT NULL,
    avatar,
    hashsum
);
