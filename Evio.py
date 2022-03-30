# Create a Process for writing data to the database
process = Process(target=databasewriteforever, args=(queue, dbconfig, write_api))
processpool.append(process)

# Start the proces
process.start()

# Wait for any of them to fail
while process.is_alive():
   time.sleep(0.01)
