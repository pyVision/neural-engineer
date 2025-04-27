# Python Logging: Preventing Propagation to Parent Loggers

Python's built-in logging module is a powerful tool for tracking events and debugging applications. This article explains how to properly configure Python's logging module to prevent log messages from propagating to parent loggers .

## Understanding Logger Hierarchy and Propagation

In Python's logging system, loggers are organized in a hierarchical namespace. For example, a logger named `foo.bar.baz` is a child of the logger named `foo.bar`, which is a child of the logger named `foo`, which is a child of the root logger.

By default, log messages propagate up this hierarchy. When you log a message to `foo.bar.baz`, that message is also sent to `foo.bar`, `foo`, and the root logger. This propagation mechanism is often the source of unwanted log messages.

Here's a simple example demonstrating logger hierarchy and propagation:

```python
import logging

def reset_logging():
    # Get the root logger
    root = logging.getLogger()
    
    # Remove all handlers from the root logger
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Reset logger hierarchy - this clears the internal dict of loggers
    logging.Logger.manager.loggerDict.clear()
    
    # Reinitialize the root logger
    logging.basicConfig(level=logging.WARNING)

# Configure the root logger with a handler
root_logger = logging.getLogger()
root_handler = logging.StreamHandler()
root_handler.setFormatter(logging.Formatter('ROOT: %(message)s'))
root_logger.addHandler(root_handler)

# Create parent logger
parent_logger = logging.getLogger('parent')
parent_handler = logging.StreamHandler()
parent_handler.setFormatter(logging.Formatter('PARENT: %(message)s'))
parent_logger.addHandler(parent_handler)

# Create child logger
child_logger = logging.getLogger('parent.child')
child_handler = logging.StreamHandler()
child_handler.setFormatter(logging.Formatter('CHILD: %(message)s'))
child_logger.addHandler(child_handler)

# Log a message with the child logger
child_logger.warning('This is a warning message')
```

When you run the above code, you'll see the warning message appears three times:

```bash
CHILD: This is a warning message
PARENT: This is a warning message
ROOT: This is a warning message
```

This happens because the log message propagates from the child logger up through the hierarchy, being handled at each level.

## The Problem with Default Propagation

Let's say you have a script that demonstrates our child, parent, and root logger hierarchy from earlier. If you simply set the root logger level to DEBUG:

```python
import logging

# Configure the root logger with a handler
root_logger = logging.getLogger()
root_handler = logging.StreamHandler()
root_handler.setFormatter(logging.Formatter('ROOT: %(message)s'))
root_logger.addHandler(root_handler)
root_logger.setLevel(logging.DEBUG)  # Set root logger to show all log levels

# Create parent logger
parent_logger = logging.getLogger('parent')
parent_handler = logging.StreamHandler()
parent_handler.setFormatter(logging.Formatter('PARENT: %(message)s'))
parent_logger.addHandler(parent_handler)
# Note: No level set, will inherit from root logger (DEBUG)

# Create child logger
child_logger = logging.getLogger('parent.child')
child_handler = logging.StreamHandler()
child_handler.setFormatter(logging.Formatter('CHILD: %(message)s'))
child_logger.addHandler(child_handler)
# Note: No level set, will inherit from parent logger (DEBUG)

# Log messages at different levels
child_logger.debug("Debug from child")    # Will propagate to all loggers
parent_logger.info("Info from parent")    # Will propagate to parent and root
root_logger.warning("Warning from root")  # Only handled by root
```

You'll not only see the DEBUG message from the child logger but also see that same message propagated to the parent and root loggers, resulting in duplicate log outputs that can quickly become overwhelming:

```bash
DEBUG:parent.child:Debug from child
DEBUG:parent:Debug from child
DEBUG:root:Debug from child
INFO:parent:Info from parent
INFO:root:Info from parent
WARNING:root:Warning from root
```

This creates a problem when:

1. You need detailed logs (DEBUG level) from your own code
2. But you want to suppress verbose output from third-party libraries
3. You're working with multiple loggers that handle the same message
4. You need different formatting for different parts of your application

Without controlling propagation, a single log event can be displayed multiple times with different formats, creating confusing and redundant output. In large applications, this can make logs practically unusable for debugging.


##  Debug Logs of Third-Party Libraries

Let's simulate a scenario where we want to see DEBUG logs from our app but not from third-party libraries:

```python
import requests, logging

# This sets up the root logger to show all messages (DEBUG and up)
logging.basicConfig(level=logging.DEBUG)  # This affects all loggers without specific levels

root_logger = logging.getLogger()

# Create our application logger
child_logger = logging.getLogger("APP")
child_logger.setLevel(logging.DEBUG)  # We want to see all APP logs
child_handler = logging.StreamHandler()
child_handler.setFormatter(logging.Formatter('CHILD: %(message)s'))
child_logger.addHandler(child_handler)
# Note: propagate is still True by default

# Make a simple HTTP request
# This will trigger many DEBUG logs from the requests and urllib3 libraries
response = requests.get('https://httpbin.org/get')

# Print the response status code
child_logger.debug(f"Response status code: {response.status_code}")
```

We can see that along logs of the request library and our module logs , we can see the duplicate logs of our application propagated to the parent

```bash
DEBUG:urllib3.connectionpool:Starting new HTTPS connection (1): httpbin.org:443
DEBUG:urllib3.connectionpool:https://httpbin.org:443 "GET /get HTTP/1.1" 200 307
CHILD: Response status code: 200
DEBUG:APP:Response status code: 200 ### logs propagated to the parent
```

## Solution: Disabling Propagation

The key to preventing log messages from propagating to parent loggers is to set the `propagate` attribute to `False` on your logger instance:

```python
import requests, logging

# This sets up the root logger to show all messages (DEBUG and up)
logging.basicConfig(level=logging.DEBUG)  # This affects all loggers without specific levels

root_logger = logging.getLogger()

# Create our application logger
child_logger = logging.getLogger("APP")
child_logger.setLevel(logging.DEBUG)  # We want to see all APP logs
child_handler = logging.StreamHandler()
child_handler.setFormatter(logging.Formatter('CHILD: %(message)s'))
child_logger.addHandler(child_handler)
#setting the propagation to parent as false
child_logger.propagate=False

# Make a simple HTTP request
# This will trigger many DEBUG logs from the requests and urllib3 libraries
response = requests.get('https://httpbin.org/get')

# Print the response status code
child_logger.debug(f"Response status code: {response.status_code}")
```


## Disable Logs for Specific Librarues

If we find that specific third party libraries are producing noisy debug logs . We can disable the logs for the specific libraries . In the below example we set the logging level of urllib3 to error whereas for all other logger the default logging level is set as DEBUG 

```python
import requests, logging

logging.basicConfig(level=logging.DEBUG)

# Create application logger for our code
child_logger = logging.getLogger("APP")
child_logger.setLevel(logging.DEBUG)  # Full visibility for our app logs
child_handler = logging.StreamHandler()
child_handler.setFormatter(logging.Formatter('CHILD: %(message)s'))
child_logger.addHandler(child_handler)

# Important: Disable propagation to parent loggers
child_logger.propagate = False  # Only our handler will process APP logs

# Special configuration for specific third-party libraries
# Example: Set urllib3 library to ERROR level only
requests_logger = logging.getLogger('urllib3')
requests_logger.setLevel(logging.ERROR)  # Only show ERROR or above for this library

# Make a simple HTTP request
# This time urllib3 DEBUG and INFO logs will be suppressed
response = requests.get('https://httpbin.org/get')

# Print the response status code
child_logger.warning(f"Response status code: {response.status_code}")
```

We can see that debug logs from urllib3 are no longer printed

```
CHILD: Response status code: 200
```

## Complete Example: Configurable Logging Setup

Let's create a reusable function to set up logging with proper propagation control:

```python
import logging
import sys

def setup_logging(app_name, app_level=logging.DEBUG, root_level=logging.WARNING):
    """Set up logging configuration that prevents propagation issues.
    
    Args:
        app_name (str): The logger name for your application
        app_level (int): Logging level for your app's logger
        root_level (int): Logging level for third-party libraries
        
    Returns:
        logging.Logger: Configured logger for your application
    """
    # Reset handlers if any exist - prevents duplicate handlers if called multiple times
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure root logger (for third-party libraries)
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)  # Usually set to WARNING to reduce noise
    
    # Add a console handler to the root logger
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(logging.Formatter('%(levelname)s - %(name)s - %(message)s'))
    root_logger.addHandler(root_handler)
    
    # Configure application logger with propagation disabled
    app_logger = logging.getLogger(app_name)
    app_logger.setLevel(app_level)  # Usually DEBUG for your own application
    app_logger.propagate = False  # Key setting to prevent propagation
    
    # Add a console handler to the application logger with more detailed formatting
    app_handler = logging.StreamHandler(sys.stdout)
    app_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    app_logger.addHandler(app_handler)
    
    # Special configuration for specific third-party libraries
    # Example: Set requests library to ERROR level only
    requests_logger = logging.getLogger('requests')
    requests_logger.setLevel(logging.ERROR)  # Only show errors from requests
    
    # Example: Completely silence urllib3
    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.setLevel(logging.CRITICAL)  # Only show critical errors from urllib3
    
    return app_logger

# Test our setup function
logger = setup_logging('my_application')

# Now let's use it
logger.debug("Application debug message - should appear")
logger.info("Application info message - should appear")

# Some third-party library logging
requests_logger = logging.getLogger('requests')
requests_logger.debug("Requests debug - should NOT appear")
requests_logger.warning("Requests warning - should appear but only if level >= WARNING")
```

we can see that output of the script consists of logs which should appear as expected

```
2025-04-27 15:44:43,471 - my_application - DEBUG - Application debug message - should appear
2025-04-27 15:44:43,473 - my_application - INFO - Application info message - should appear
```


## Best Practices Summary

1. **Always set explicit log levels** for your application loggers
2. **Disable propagation** by setting `propagate=False` on application loggers
3. **Add appropriate handlers** to loggers with disabled propagation
4. **Configure the root logger** to control third-party library logging
5. **Explicitly configure problematic third-party loggers** when needed
6. **Consider using a configuration file** for complex applications


## Conclusion

By understanding how logger propagation works in Python and taking control of it, you can create a clean logging setup that shows exactly the information you need without noise from dependencies.

The key takeaway is to set `propagate=False` on your application loggers and add appropriate handlers to them, while configuring the root logger to manage third-party libraries' log levels.

With these techniques in place, you'll have a much more manageable and useful logging system that provides the information you need without overwhelming you with irrelevant messages.
