import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler
from ai_agent import PawPalAgent
from knowledge_base import KnowledgeBase
from datetime import datetime, date, timedelta
import pandas as pd

# Check if Owner instance exists in session state before creating a new one
if 'owner' not in st.session_state:
    st.session_state.owner = None  # Placeholder; will be set based on user input
if 'agent' not in st.session_state:
    st.session_state.agent = PawPalAgent()
if 'last_ai_response' not in st.session_state:
    st.session_state.last_ai_response = None
if 'last_ai_pet' not in st.session_state:
    st.session_state.last_ai_pet = None

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to PawPal+, your pet care planning assistant.

This app helps you track and organize pet care tasks with smart sorting, conflict detection, and scheduling.
"""
)

st.divider()

# ===== SECTION: CREATE OWNER AND PET =====
st.subheader("1. Set Up Owner & Pets")

col1, col2, col3 = st.columns(3)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan", key="owner_name_input")
with col2:
    owner_age = st.number_input("Owner age", min_value=1, max_value=120, value=30, key="owner_age_input")
with col3:
    create_owner = st.button("Create Owner", key="create_owner_btn")

if create_owner:
    if st.session_state.owner is None:
        st.session_state.owner = Owner(name=owner_name, age=owner_age)
        st.success(f"✅ Created owner '{owner_name}'!")
    else:
        st.info("Owner already created.")

# Display current owner
if st.session_state.owner:
    st.info(f"👤 Owner: {st.session_state.owner.name} (Age: {st.session_state.owner.age})")

# Add pet section
st.markdown("### Add Pets")
col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi", key="pet_name_input")
with col2:
    species = st.selectbox("Species", ["Dog", "Cat", "Bird", "Fish", "Rabbit"], key="species_input")
with col3:
    add_pet = st.button("Add Pet", key="add_pet_btn")

if add_pet:
    if st.session_state.owner:
        # Check if pet already exists
        if not any(p.name == pet_name for p in st.session_state.owner.pets):
            pet = Pet(name=pet_name, kind_of_animal=species, owner=st.session_state.owner)
            st.session_state.owner.add_pet(pet)
            st.success(f"🐾 Added '{pet_name}' the {species}!")
        else:
            st.warning(f"Pet '{pet_name}' already exists.")
    else:
        st.error("Please create an owner first.")

# Display current pets
if st.session_state.owner and st.session_state.owner.pets:
    st.markdown("### Current Pets")
    pet_cols = st.columns(len(st.session_state.owner.pets))
    for idx, pet in enumerate(st.session_state.owner.pets):
        with pet_cols[idx]:
            st.write(f"**{pet.name}**")
            st.caption(f"{pet.kind_of_animal}")
            st.caption(f"_{pet.get_animal_needs()}_")

st.divider()

# ===== SECTION: MANAGE TASKS =====
st.subheader("2. Manage Tasks")

if st.session_state.owner and st.session_state.owner.pets:
    pet_names = [p.name for p in st.session_state.owner.pets]
    selected_pet_name = st.selectbox("Select pet", pet_names, key="task_pet_select")
    selected_pet = next(p for p in st.session_state.owner.pets if p.name == selected_pet_name)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        task_description = st.text_input("Task description", value="Feed", key="task_desc_input")
    with col2:
        task_hour = st.number_input("Hour", min_value=0, max_value=23, value=9, key="task_hour_input")
    with col3:
        task_minute = st.number_input("Minute", min_value=0, max_value=59, value=0, key="task_minute_input")
    with col4:
        frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly", "yearly", "none"], key="task_freq_input")
    with col5:
        add_task = st.button("Add Task", key="add_task_btn")

    if add_task:
        task_time = datetime.now().replace(hour=task_hour, minute=task_minute, second=0, microsecond=0)
        task = Task(
            description=task_description,
            time=task_time,
            frequency=frequency,
            pet=selected_pet
        )
        selected_pet.add_task(task)
        st.success(f"✅ Added '{task_description}' for {selected_pet_name}!")

    # Display tasks for selected pet
    if selected_pet.tasks:
        st.markdown(f"### Tasks for {selected_pet_name}")
        
        # Create task table
        task_data = []
        for task in selected_pet.tasks:
            task_data.append({
                "Description": task.description,
                "Time": task.time.strftime("%H:%M"),
                "Frequency": task.frequency,
                "Status": "✅ Complete" if task.completion_status else "⏳ Pending"
            })
        
        df = pd.DataFrame(task_data)
        st.table(df)
    else:
        st.info(f"No tasks yet for {selected_pet_name}. Add one above!")
else:
    st.info("Create an owner and add at least one pet to manage tasks.")

st.divider()

# ===== SECTION: VIEW SCHEDULE =====
st.subheader("3. View & Manage Schedule")

if st.session_state.owner and st.session_state.owner.pets and any(len(p.tasks) > 0 for p in st.session_state.owner.pets):
    scheduler = Scheduler(st.session_state.owner)
    
    # Check for conflicts
    conflict_warning = scheduler.check_for_conflicts()
    if conflict_warning:
        st.warning(f"⚠️ {conflict_warning}")
    else:
        st.success("✅ No scheduling conflicts detected!")
    
    # Filter and display options
    col1, col2 = st.columns(2)
    
    with col1:
        view_option = st.radio(
            "View",
            ["All Tasks (Sorted)", "Today's Tasks", "By Pet", "By Status"],
            horizontal=True
        )
    
    with col2:
        if view_option == "By Pet":
            pet_filter = st.selectbox("Filter by pet", pet_names, key="view_pet_filter")
        elif view_option == "By Status":
            status_filter = st.selectbox("Filter by status", ["Pending", "Completed"], key="view_status_filter")
    
    # Get and display tasks based on selection
    if view_option == "All Tasks (Sorted)":
        all_tasks = scheduler.get_all_tasks(sort_by_time=True)
        if all_tasks:
            st.markdown("### All Tasks (Sorted by Time)")
            task_data = []
            for task in all_tasks:
                task_data.append({
                    "Time": task.time.strftime("%H:%M"),
                    "Description": task.description,
                    "Pet": task.pet.name,
                    "Frequency": task.frequency,
                    "Status": "✅ Complete" if task.completion_status else "⏳ Pending"
                })
            df = pd.DataFrame(task_data)
            st.table(df)
        else:
            st.info("No tasks to display.")
    
    elif view_option == "Today's Tasks":
        today_tasks = scheduler.get_today_tasks()
        if today_tasks:
            st.markdown(f"### Today's Schedule ({datetime.now().strftime('%A, %B %d')})")
            for task in today_tasks:
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.write(f"**{task.time.strftime('%H:%M')}**")
                with col2:
                    st.write(f"{task.description} ← {task.pet.name}")
                with col3:
                    if task.completion_status:
                        st.write("✅")
                    else:
                        st.write("⏳")
        else:
            st.info(f"No tasks scheduled for today ({datetime.now().strftime('%A, %B %d')}).")
    
    elif view_option == "By Pet":
        pet_tasks = scheduler.get_tasks_for_pet(pet_filter, sort_by_time=True)
        if pet_tasks:
            st.markdown(f"### {pet_filter}'s Tasks (Sorted by Time)")
            task_data = []
            for task in pet_tasks:
                task_data.append({
                    "Time": task.time.strftime("%H:%M"),
                    "Description": task.description,
                    "Frequency": task.frequency,
                    "Status": "✅ Complete" if task.completion_status else "⏳ Pending"
                })
            df = pd.DataFrame(task_data)
            st.table(df)
        else:
            st.info(f"No tasks for {pet_filter}.")
    
    elif view_option == "By Status":
        is_completed = status_filter == "Completed"
        status_tasks = scheduler.get_tasks_by_status(completed=is_completed, sort_by_time=True)
        if status_tasks:
            status_title = "Completed" if is_completed else "Pending"
            st.markdown(f"### {status_title} Tasks (Sorted by Time)")
            task_data = []
            for task in status_tasks:
                task_data.append({
                    "Time": task.time.strftime("%H:%M"),
                    "Description": task.description,
                    "Pet": task.pet.name,
                    "Frequency": task.frequency
                })
            df = pd.DataFrame(task_data)
            st.table(df)
        else:
            st.info(f"No {status_filter.lower()} tasks.")

else:
    st.info("Add tasks to your pets to view and manage the schedule.")

st.divider()

# ===== SECTION: AI ASSISTANT =====
st.subheader("4. AI Assistant")

st.markdown(
    "Generate a personalized care plan for your pet using the AI agent, "
    "or analyze your current schedule for conflicts and gaps."
)

if st.session_state.owner and st.session_state.owner.pets:
    _kb = KnowledgeBase()

    col1, col2, col3 = st.columns(3)
    with col1:
        ai_pet_name = st.selectbox(
            "Select pet", [p.name for p in st.session_state.owner.pets], key="ai_pet_select"
        )
    ai_pet = next(p for p in st.session_state.owner.pets if p.name == ai_pet_name)
    available_breeds = _kb.get_available_breeds(ai_pet.kind_of_animal)

    with col2:
        breed_options = ["(no specific breed)"] + available_breeds
        breed_selection = st.selectbox("Breed (optional)", breed_options, key="ai_breed_select")
        selected_breed = None if breed_selection == "(no specific breed)" else breed_selection

    with col3:
        st.write("")  # vertical alignment spacer
        st.write("")
        generate_btn = st.button("Generate Care Plan", key="generate_plan_btn", use_container_width=True)

    analyze_btn = st.button("Analyze My Schedule", key="analyze_schedule_btn")

    if generate_btn:
        with st.spinner("Generating care plan..."):
            response = st.session_state.agent.generate_care_plan(
                pet=ai_pet,
                breed=selected_breed,
                owner=st.session_state.owner,
            )
            st.session_state.last_ai_response = response
            st.session_state.last_ai_pet = ai_pet

    if analyze_btn:
        with st.spinner("Analyzing schedule..."):
            response = st.session_state.agent.analyze_schedule(st.session_state.owner)
            st.session_state.last_ai_response = response
            st.session_state.last_ai_pet = None

    # Display the AI response
    if st.session_state.last_ai_response:
        response = st.session_state.last_ai_response
        st.markdown("---")

        if response.success:
            st.markdown(response.message)

            # Confidence badge
            conf = response.confidence_score
            if conf >= 0.8:
                st.success(f"Confidence: {conf:.0%}")
            elif conf >= 0.5:
                st.warning(f"Confidence: {conf:.0%}")
            else:
                st.error(f"Confidence: {conf:.0%} — limited data for this animal type")

            # Offer to add suggested tasks
            if response.suggested_tasks and st.session_state.last_ai_pet:
                pet_for_tasks = st.session_state.last_ai_pet
                conflict_free = [t for t in response.suggested_tasks if not t.get("has_conflict")]
                conflicting = [t for t in response.suggested_tasks if t.get("has_conflict")]

                if conflicting:
                    st.warning(
                        f"{len(conflicting)} suggested task(s) overlap with your existing schedule "
                        f"and will be skipped. Only {len(conflict_free)} non-conflicting tasks will be added."
                    )

                if conflict_free:
                    if st.button(
                        f"Add {len(conflict_free)} suggested tasks to {pet_for_tasks.name}'s schedule",
                        key="add_suggested_btn",
                    ):
                        today = date.today()
                        for task_info in conflict_free:
                            task_time = datetime.combine(
                                today,
                                datetime.min.time().replace(
                                    hour=task_info["hour"], minute=task_info["minute"]
                                ),
                            )
                            new_task = Task(
                                description=task_info["description"],
                                time=task_time,
                                frequency=task_info.get("frequency", "daily"),
                                pet=pet_for_tasks,
                            )
                            pet_for_tasks.add_task(new_task)
                        st.success(f"Added {len(conflict_free)} tasks to {pet_for_tasks.name}'s schedule!")
                        st.session_state.last_ai_response = None
                        st.rerun()
        else:
            st.error(response.message)
else:
    st.info("Create an owner and add at least one pet to use the AI assistant.")
