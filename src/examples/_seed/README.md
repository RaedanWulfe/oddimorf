# Creating from template
Creating a new component from the included component seed, updating the config and script file through to use in a chain.

> Note: components are single input, multiple output (SIMO).

---
1. Copy the **``.\_seed``** directory, then rename the copy as appropriate.

---
2. Open the component's **``config.yml``** file, then provide:

   * A Globally Unique Identifier (GUID)

   * Component name

   * Test broker details

---
3. Set up the outgoing data schema:

   * Trim out the unused configurations in the commented out ``dataSchema`` sections, commenting in the data type seeds intended for use and duplicating these where necessary.

   * Provide a unique identifier key (PascalCase preferred) to each of the schema's data channels.

   * Trim down the channel sub-sections and rename the fields as appropriate.

   * Define the anticipated data refresh period, which will also be used as a factor in the timeouts of these elements on the UI.

---
4. Set up the requisite control schema:

   * Trim out the unused configurations in the commented out ``controlSchema`` sections, commenting in the control type seeds intended for use and duplicating these where necessary.

   * Provide a GUID and descriptive label to each of the schema's controls.

   * With checkbox or radio elements, trim out or extend control sub-sections as necessary - then provide labels for each of the button components.

   * Provide the necessary default values and boundary conditions as provided for in the control configurations.

---

5. Open the primary script file, then set up the read and write queues:

   * If the component is the first/only component in the processing chain, remove the read queue sections from the async loop function.

   * Define the read queue data fields as necessary.

   * Define the write queues as provided in the **``config.yml``** file's ``dataSchema``.

---
6. Assign each item from the context controls list to a named variable for ease of use.

---
7. Specify the primary logic where indicated in the processing loop:

   * Import any libraries that will be needed, also add non standard library items to the the **``requirements.txt``** file to simplify usage.

   * When populating the write queues, make sure that the items adhere to what has been provided for these channels in the accompanying **``config.yml``** file.

---
8. Once complete, create a new chain with the newly added component and verify its operation.

---