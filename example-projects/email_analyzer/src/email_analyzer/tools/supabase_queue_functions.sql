-- Enable the pg_message_queue extension
create extension if not exists pg_message_queue;

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

-- Create a function to dequeue messages
create or replace function public.dequeue(
    queue_name text
)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
    message_record record;
    result jsonb;
begin
    -- Try to get a message from the queue
    select * into message_record 
    from pgmq.read(queue_name, 1) 
    limit 1;
    
    if message_record is null then
        return null;
    end if;
    
    -- Delete the message after processing
    perform pgmq.delete(queue_name, ARRAY[message_record.msg_id]);
    
    -- Return the message payload
    return message_record.message::jsonb;
end;
$$;

-- Create a function to peek at messages without dequeuing
create or replace function public.peek_queue(
    queue_name text
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    message_record record;
begin
    -- Get a message without removing it
    select * into message_record 
    from pgmq.read(queue_name, 1) 
    limit 1;
    
    if message_record is null then
        return null;
    end if;
    
    return message_record.message::jsonb;
end;
$$;

-- Create a function to get queue length
create or replace function public.get_queue_length(
    queue_name text
)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare
    queue_size bigint;
begin
    select count(*) into queue_size
    from pgmq.read(queue_name, null);
    
    return queue_size;
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
    perform pgmq.delete_queue(queue_name);
    perform pgmq.create_queue(queue_name);
end;
$$;



-- Create RLS policies for queue access
create policy "Enable all access for authenticated users"
on pgmq.message_queue
for all
to authenticated
using (true);