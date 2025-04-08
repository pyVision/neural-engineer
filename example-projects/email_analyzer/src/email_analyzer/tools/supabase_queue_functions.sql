

-- emails table
create table if not exists emails  (
    msg_id text primary key,
    email_data text
);



-- checkpoints table
create table if not exists checkpoints (
    key text primary key,
    value text
);

-- -- Enable the pg_message_queue extension
-- create extension if not exists pg_message_queue;

-- Create a function to enqueue messages
create or replace function public.enqueue(
    queue_name text,
    message_payload jsonb
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    -- Insert the message into the queue
    perform pgmq.send(
        queue_name,
        message_payload::jsonb
    );
end;
$$;


CREATE TYPE my_tuple AS (
    msg_id bigint,
    data jsonb
);

drop function dequeue;
-- Create a function to dequeue messages
create or replace function public.dequeue(
    queue_name text,
    msg_id bigint
)
RETURNS my_tuple
language plpgsql
security definer
set search_path = public
as $$
declare
    message_record record;
    --result jsonb;
    result my_tuple;
begin
    -- Try to get a message from the queue

    result.msg_id := message_record.msg_id;
    result.data :=message_record.message;
    if msg_id is null then
     select * into message_record 
     from pgmq.read(queue_name, 30,1) 
     limit 1;
     msg_id := message_record.msg_id;
    end if;

    
    
    -- Delete the message after processing
    perform pgmq.delete(queue_name, ARRAY[msg_id]);
    
    result.msg_id := msg_id;
    result.data :=null;
    
    RETURN result;
end;
$$;

drop function peek_queue;



-- Create a function to peek at messages without dequeuing
create or replace function public.peek_queue(
    queue_name text

)
RETURNS my_tuple
language plpgsql
security definer
set search_path = public
as $$
declare
    result my_tuple;
    message_record record;
begin

    result.msg_id := null;
    result.data :=null;

    -- Get a message without removing it
    select * into message_record 
    from pgmq.read(queue_name,30,1);
    -- limit 1;
    
    if message_record is null then
      return result;
    end if;
    result.msg_id := message_record.msg_id;
    result.data :=message_record.message;
    
    RETURN result;
end;
$$;



-- Create a function to purge a queue
create or replace function public.purge_queue(
    queue_name text
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    perform pgmq.purge_queue(queue_name);
    --perform pgmq.create_queue(queue_name);
end;
$$;

-- Create RLS policies for queue access
create policy "Enable all access for authenticated users"
on pgmq.message_queue
for all
to authenticated
using (true);