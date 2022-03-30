# Create a Process for writing data to the database
process = Process(target=evaluate_have, args=())

# Start the proces
process.start()

# Wait for any of them to fail
while process.is_alive():
   time.sleep(0.01)
