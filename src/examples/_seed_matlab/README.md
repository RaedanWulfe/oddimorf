# Creating from template for Matlab
Creating a new component from the included component seed, updating the config and script file through to use in a chain.

> Note: components are single input, multiple output (SIMO).

---
1. Copy the **``.\_seed_matlab``** directory, then rename the copy as appropriate.

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
5. Open the primary script file, the Matlab process file and the separate structure application file, then set up the read and write queues:

   * If the component is the first/only component in the processing chain, remove the reader sections from the script.

   * **[OPTIONAL]** Set the incoming/read queue channel name:

      * In the Python script's primary async loop.

      * In the Matlab process script's incoming data sections as the **``*.dat``** file name (prepend with an underscore).

      * In the Matlab structure application script's incoming data sections as the **``*.dat``** file name (prepend with an underscore).

   * **[OPTIONAL]** Define the read queue data fields as necessary:

      * In the Python script's ``Reader`` class.

      * In the Matlab process script's incoming data sections.

      * In the Matlab process script's primary loop, within the section indicating interpretation of the data fields. Use the commented out code as a guide, duplicating as necessary.

      iv.  In the Matlab structure application script's incoming data sections.

   * Duplicate to the number of required outgoing channels, then set the outgoing/write queue channel names:

      * In the Matlab process script's incoming data sections as the **``*.dat``** file name (prepend with an underscore).

      * In the Matlab structure application script's incoming data sections as the **``*.dat``** file name (prepend with an underscore).

   * Define the write queue data fields as necessary:

      * In the Matlab process script's outgoing data sections.

      * In the Matlab structure application script's outgoing data sections.

---
6. Set up the control fields:

   * Define control set functions in the Python script's ``Interpreter`` class, associating fields with the class as necessary and wiring the fields in to the control struct.

   * Wire up the controls as shown in the Python script's primary loop with the commented out examples, duplicate as necessary.

   * Add the necessary control fields as necessary:

      * In the Matlab process script's control section.

      * In the Matlab structure application script's control section.

---
7. Specify the primary logic where indicated in the Matlab process script, this can be very implementation specific and not covered here.

   > Note: When populating the write queues, make sure that the items adhere to what has been provided for these channels in the accompanying **``config.yml``** file.

---
8. Once complete, create a new chain with the newly added component and verify its operation.

---
