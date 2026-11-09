import json
import os
from datetime import datetime
from graph.workflow import create_content_workflow

def main():
    print("--- Content Generation Pipeline Verification ---")
    
    # Ensure environment is ready
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not found in environment.")
        return

    print("Initializing workflow...")
    app = create_content_workflow()
    
    # Request that hits our mock data well
    request = "Write a comprehensive blog post about the benefits of green tea."
    print(f"\nProcessing Request: '{request}'")
    
    initial_state = {
        "content_request": request,
        "settings": {
            "word_count": 800,
            "tone": "informative"
        }
    }
    
    try:
        # Run workflow
        result = app.invoke(initial_state, config={"configurable": {"thread_id": "smoke"}})
        
        print("\n--- Workflow Completed Successfully ---")
        
        # Save Outputs
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Save Brief
        if result.get("brief"):
            with open(f"{output_dir}/brief_{timestamp}.json", "w") as f:
                json.dump(result["brief"], f, indent=2)
            print(f"✅ Brief saved to outputs/brief_{timestamp}.json")
            
        # 2. Save Research
        if result.get("research_findings"):
            with open(f"{output_dir}/research_{timestamp}.md", "w") as f:
                f.write(result["research_findings"])
            print(f"✅ Research saved to outputs/research_{timestamp}.md")

        # 3. Save Final Content
        final_content = result.get("final_content")
        if final_content:
            filename = f"{output_dir}/final_content_{timestamp}.md"
            with open(filename, "w") as f:
                f.write(final_content)
            print(f"✅ Final Content saved to {filename}")
            
            # Print preview
            print("\n--- Content Preview ---")
            print(final_content[:500] + "...\n")
            
        # 4. Save Metadata
        seo_meta = result.get("seo_metadata")
        if seo_meta:
            with open(f"{output_dir}/metadata_{timestamp}.json", "w") as f:
                json.dump(seo_meta, f, indent=2)
            print(f"✅ SEO Metadata saved to outputs/metadata_{timestamp}.json")

        if result.get('errors'):
            print("\n❌ Errors encountered:")
            for error in result['errors']:
                print(f"- {error}")
            
    except Exception as e:
        print(f"\n❌ Workflow FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
