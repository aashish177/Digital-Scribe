from vector_stores.chroma import ChromaDBManager
db = ChromaDBManager()

# Let's map collection names to their internal names:
for logical_name, collection_name in db.COLLECTIONS.items():
    try:
        coll = db.client.get_collection(collection_name)
        print(f"Collection '{logical_name}' ({collection_name}) has {coll.count()} documents.")
    except ValueError as e:
        print(f"Collection '{logical_name}' ({collection_name}) does not exist yet. Error: {e}")
    except Exception as e:
        print(f"Error accessing '{logical_name}' ({collection_name}): {e}")
