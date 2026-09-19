def sqlite_schema() -> list[str]:
    return [
        """
        create table if not exists users (
            id integer primary key autoincrement,
            username text not null unique,
            password_hash text not null,
            role text not null default 'user',
            created_at text not null
        )
        """,
        """
        create table if not exists notes (
            id integer primary key autoincrement,
            partner text not null,
            feeling text not null,
            body text not null,
            created_at text not null
        )
        """,
        """
        create table if not exists replies (
            id integer primary key autoincrement,
            note_id integer not null,
            body text not null,
            created_at text not null,
            foreign key (note_id) references notes (id)
        )
        """,
        """
        create table if not exists note_media (
            id integer primary key autoincrement,
            note_id integer not null,
            file_name text not null,
            media_type text not null,
            foreign key (note_id) references notes (id)
        )
        """,
        """
        create table if not exists memories (
            id integer primary key autoincrement,
            file_name text not null,
            media_type text not null,
            content_hash text,
            created_at text not null
        )
        """,
    ]


def azure_sql_schema() -> list[str]:
    return [
        """
        if object_id('dbo.users', 'U') is null
            create table dbo.users (
                id int identity(1,1) primary key,
                username nvarchar(255) not null unique,
                password_hash nvarchar(255) not null,
                role nvarchar(50) not null default 'user',
                created_at datetime2 not null
            )
        """,
        """
        if object_id('dbo.notes', 'U') is null
            create table dbo.notes (
                id int identity(1,1) primary key,
                partner nvarchar(255) not null,
                feeling nvarchar(255) not null,
                body nvarchar(max) not null,
                created_at datetime2 not null
            )
        """,
        """
        if object_id('dbo.replies', 'U') is null
            create table dbo.replies (
                id int identity(1,1) primary key,
                note_id int not null,
                body nvarchar(max) not null,
                created_at datetime2 not null,
                constraint fk_replies_notes foreign key (note_id) references dbo.notes(id)
            )
        """,
        """
        if object_id('dbo.note_media', 'U') is null
            create table dbo.note_media (
                id int identity(1,1) primary key,
                note_id int not null,
                file_name nvarchar(255) not null,
                media_type nvarchar(255) not null,
                constraint fk_note_media_notes foreign key (note_id) references dbo.notes(id)
            )
        """,
        """
        if object_id('dbo.memories', 'U') is null
            create table dbo.memories (
                id int identity(1,1) primary key,
                file_name nvarchar(255) not null,
                media_type nvarchar(255) not null,
                content_hash nvarchar(128) null,
                created_at datetime2 not null
            )
        """,
    ]
